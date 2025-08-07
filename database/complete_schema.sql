-- Melbourne Parking System Complete Database Schema
-- Integrates suburbs and parking data with spatial relationships

-- Drop existing tables if exist (in correct order due to foreign keys)
DROP TABLE IF EXISTS parking_spaces CASCADE;
DROP TABLE IF EXISTS off_street_parking CASCADE;
DROP TABLE IF EXISTS suburbs CASCADE;
DROP TABLE IF EXISTS off_street_car_parks CASCADE;
DROP TABLE IF EXISTS vic_suburb_boundaries CASCADE;

-- 1. Create suburbs table (master reference table)
CREATE TABLE suburbs (
    id SERIAL PRIMARY KEY,
    lc_ply_pid INTEGER UNIQUE,                    -- Original polygon ID
    loc_pid VARCHAR(20),                          -- Location PID (e.g., VIC1962)
    suburb_name VARCHAR(100) NOT NULL,            -- Suburb name
    state VARCHAR(10) DEFAULT 'VIC',              -- State
    postcode VARCHAR(10),                         -- Postcode
    geometry_type VARCHAR(20),                    -- Geometry type (MultiPolygon/Polygon)
    coordinates JSONB,                            -- GeoJSON coordinates for map display
    created_date TIMESTAMP,                       -- Creation date
    retired_date TIMESTAMP,                       -- Retirement date (if any)
    last_updated TIMESTAMP,                       -- Last update timestamp

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Create off_street_parking table (commercial parking from 2022)
CREATE TABLE off_street_parking (
    id SERIAL PRIMARY KEY,
    census_year VARCHAR(4) NOT NULL,              -- Census year (2022)
    block_id INTEGER,                             -- Block identifier
    property_id VARCHAR(20),                      -- Property ID
    base_property_id VARCHAR(20),                 -- Base property ID
    building_address TEXT NOT NULL,               -- Full address
    parking_type VARCHAR(50) DEFAULT 'Commercial', -- Parking type
    parking_spaces INTEGER NOT NULL DEFAULT 0,    -- Number of parking spaces
    latitude DECIMAL(10, 8) NOT NULL,            -- Latitude coordinate
    longitude DECIMAL(11, 8) NOT NULL,           -- Longitude coordinate

    -- Foreign key to suburbs (will be populated via spatial matching)
    suburb_id INTEGER REFERENCES suburbs(id),

    -- Derived fields
    suburb_name VARCHAR(100),                     -- Cached suburb name for quick queries
    postcode VARCHAR(10),                         -- Cached postcode for quick queries

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Off-street car parks table
CREATE TABLE IF NOT EXISTS off_street_car_parks (
    id SERIAL PRIMARY KEY,
    census_year INTEGER,
    block_id VARCHAR(255),
    property_id VARCHAR(255),
    base_property_id VARCHAR(255),
    building_address TEXT,
    clue_small_area VARCHAR(255),
    parking_type VARCHAR(100),
    parking_spaces INTEGER,
    longitude DECIMAL(10, 8),
    latitude DECIMAL(10, 8),
    location JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Suburb boundaries table
CREATE TABLE IF NOT EXISTS vic_suburb_boundaries (
    id SERIAL PRIMARY KEY,
    suburb_name VARCHAR(255),
    postcode VARCHAR(10),
    state VARCHAR(10),
    geometry JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Create parking_spaces table for real-time data (future use)
CREATE TABLE parking_spaces (
    id SERIAL PRIMARY KEY,
    off_street_parking_id INTEGER REFERENCES off_street_parking(id),
    space_number INTEGER,                         -- Individual space number
    status VARCHAR(20) DEFAULT 'available',      -- available, occupied, reserved, out_of_service
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(off_street_parking_id, space_number)
);

-- Create indexes for performance
-- Suburbs indexes
CREATE INDEX idx_suburbs_name ON suburbs(suburb_name);
CREATE INDEX idx_suburbs_postcode ON suburbs(postcode);
CREATE INDEX idx_suburbs_loc_pid ON suburbs(loc_pid);
CREATE INDEX idx_suburbs_lc_ply_pid ON suburbs(lc_ply_pid);

-- Parking indexes
CREATE INDEX idx_parking_location ON off_street_parking(latitude, longitude);
CREATE INDEX idx_parking_suburb_id ON off_street_parking(suburb_id);
CREATE INDEX idx_parking_suburb_name ON off_street_parking(suburb_name);
CREATE INDEX idx_parking_postcode ON off_street_parking(postcode);
CREATE INDEX idx_parking_address ON off_street_parking USING GIN(to_tsvector('english', building_address));
CREATE INDEX idx_parking_spaces_count ON off_street_parking(parking_spaces);

-- Parking spaces indexes
CREATE INDEX idx_spaces_parking_id ON parking_spaces(off_street_parking_id);
CREATE INDEX idx_spaces_status ON parking_spaces(status);

-- Off-street car parks indexes
CREATE INDEX IF NOT EXISTS idx_off_street_parking_location ON off_street_car_parks USING GIST ((longitude, latitude));
CREATE INDEX IF NOT EXISTS idx_off_street_parking_type ON off_street_car_parks(parking_type);
CREATE INDEX IF NOT EXISTS idx_off_street_clue_area ON off_street_car_parks(clue_small_area);

-- Suburb boundaries indexes
CREATE INDEX IF NOT EXISTS idx_suburb_boundaries_name ON vic_suburb_boundaries(suburb_name);
CREATE INDEX IF NOT EXISTS idx_suburb_boundaries_postcode ON vic_suburb_boundaries(postcode);

-- Create functions for spatial operations
-- Function to find suburb for a given coordinate
CREATE OR REPLACE FUNCTION find_suburb_by_coordinate(lat DECIMAL, lng DECIMAL)
RETURNS TABLE(suburb_id INTEGER, suburb_name VARCHAR, postcode VARCHAR) AS $$
BEGIN
    -- This is a simplified version - in production you'd use PostGIS ST_Contains
    -- For now, we'll use a simple distance-based approach
    RETURN QUERY
    SELECT s.id, s.suburb_name, s.postcode
    FROM suburbs s
    WHERE s.suburb_name IS NOT NULL
    ORDER BY (
        -- Simple distance calculation (not accurate for large distances)
        (lat - (s.coordinates->'coordinates'->0->0->0->1)::decimal)^2 +
        (lng - (s.coordinates->'coordinates'->0->0->0->0)::decimal)^2
    ) ASC
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

-- Function to update parking suburb associations
CREATE OR REPLACE FUNCTION update_parking_suburb_associations()
RETURNS INTEGER AS $$
DECLARE
    parking_record RECORD;
    suburb_info RECORD;
    updated_count INTEGER := 0;
BEGIN
    FOR parking_record IN
        SELECT id, latitude, longitude FROM off_street_parking
        WHERE suburb_id IS NULL
    LOOP
        -- Find the closest suburb (simplified)
        SELECT INTO suburb_info s.id, s.suburb_name, s.postcode
        FROM suburbs s
        WHERE s.suburb_name IS NOT NULL
        ORDER BY (
            (parking_record.latitude - COALESCE((s.coordinates->'coordinates'->0->0->0->1)::decimal, 0))^2 +
            (parking_record.longitude - COALESCE((s.coordinates->'coordinates'->0->0->0->0)::decimal, 0))^2
        ) ASC
        LIMIT 1;

        IF suburb_info.id IS NOT NULL THEN
            UPDATE off_street_parking
            SET suburb_id = suburb_info.id,
                suburb_name = suburb_info.suburb_name,
                postcode = suburb_info.postcode
            WHERE id = parking_record.id;

            updated_count := updated_count + 1;
        END IF;
    END LOOP;

    RETURN updated_count;
END;
$$ LANGUAGE plpgsql;

-- Create views for common queries
-- View: Suburb parking summary
CREATE VIEW suburb_parking_summary AS
SELECT
    s.id as suburb_id,
    s.suburb_name,
    s.postcode,
    COUNT(p.id) as total_parking_facilities,
    COALESCE(SUM(p.parking_spaces), 0) as total_parking_spaces,
    COALESCE(AVG(p.parking_spaces), 0)::INTEGER as avg_spaces_per_facility
FROM suburbs s
LEFT JOIN off_street_parking p ON s.id = p.suburb_id
WHERE s.suburb_name IS NOT NULL
GROUP BY s.id, s.suburb_name, s.postcode
ORDER BY total_parking_spaces DESC;

-- View: Parking facilities with suburb info
CREATE VIEW parking_with_suburb AS
SELECT
    p.id,
    p.building_address,
    p.parking_spaces,
    p.latitude,
    p.longitude,
    s.suburb_name,
    s.postcode,
    s.loc_pid as suburb_loc_pid
FROM off_street_parking p
LEFT JOIN suburbs s ON p.suburb_id = s.id;

-- Example data queries that will be useful:

-- 1. Query parking by suburb name
-- SELECT * FROM parking_with_suburb WHERE suburb_name ILIKE '%melbourne%';

-- 2. Query parking by postcode
-- SELECT * FROM parking_with_suburb WHERE postcode = '3000';

-- 3. Get suburb parking statistics
-- SELECT * FROM suburb_parking_summary WHERE total_parking_facilities > 0;

-- 4. Find nearest parking to a coordinate
-- SELECT *,
--        SQRT(POW(latitude - (-37.8136), 2) + POW(longitude - 144.9631, 2)) as distance
-- FROM parking_with_suburb
-- ORDER BY distance LIMIT 10;

-- 5. Search parking by address
-- SELECT * FROM parking_with_suburb
-- WHERE building_address ILIKE '%collins%street%';

-- Insert trigger to automatically update timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_suburbs_updated_at BEFORE UPDATE ON suburbs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_parking_updated_at BEFORE UPDATE ON off_street_parking
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

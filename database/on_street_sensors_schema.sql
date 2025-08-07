-- Melbourne On-Street Parking Sensors Database Schema
-- Stores real-time parking sensor data from Melbourne Government Open Data

-- Drop existing table if exists
DROP TABLE IF EXISTS on_street_sensors CASCADE;

-- Create on_street_sensors table
CREATE TABLE on_street_sensors (
    id SERIAL PRIMARY KEY,
    kerbside_id INTEGER NOT NULL UNIQUE,                    -- Unique kerbside sensor ID
    zone_number INTEGER,                                    -- Parking zone number (can be null)
    status_description VARCHAR(50) NOT NULL,                -- Status: "Present", "Unoccupied", etc.
    last_updated TIMESTAMP WITH TIME ZONE NOT NULL,         -- Last update timestamp
    status_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,     -- Status change timestamp
    latitude DECIMAL(10, 8) NOT NULL,                       -- Latitude coordinate
    longitude DECIMAL(11, 8) NOT NULL,                      -- Longitude coordinate
    
    -- Foreign key to suburbs (will be populated via spatial matching)
    suburb_id INTEGER REFERENCES suburbs(id),
    
    -- Derived fields for quick queries
    suburb_name VARCHAR(100),                               -- Cached suburb name
    postcode VARCHAR(10),                                   -- Cached postcode
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX idx_on_street_sensors_kerbside_id ON on_street_sensors(kerbside_id);
CREATE INDEX idx_on_street_sensors_zone_number ON on_street_sensors(zone_number);
CREATE INDEX idx_on_street_sensors_status ON on_street_sensors(status_description);
CREATE INDEX idx_on_street_sensors_location ON on_street_sensors(latitude, longitude);
CREATE INDEX idx_on_street_sensors_last_updated ON on_street_sensors(last_updated);
CREATE INDEX idx_on_street_sensors_suburb ON on_street_sensors(suburb_name);

-- Create unique constraint on kerbside_id
ALTER TABLE on_street_sensors ADD CONSTRAINT unique_kerbside_id UNIQUE (kerbside_id);

-- Create trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_on_street_sensors_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_on_street_sensors_updated_at
    BEFORE UPDATE ON on_street_sensors
    FOR EACH ROW
    EXECUTE FUNCTION update_on_street_sensors_updated_at();

-- Create function to find suburb by coordinate
CREATE OR REPLACE FUNCTION find_suburb_for_sensor(
    sensor_lat DECIMAL,
    sensor_lon DECIMAL
) RETURNS INTEGER AS $$
DECLARE
    suburb_id_result INTEGER;
BEGIN
    SELECT id INTO suburb_id_result
    FROM suburbs
    WHERE ST_Contains(
        ST_GeomFromGeoJSON(
            json_build_object(
                'type', 'Point',
                'coordinates', ARRAY[sensor_lon, sensor_lat]
            )::text
        ),
        ST_GeomFromGeoJSON(
            json_build_object(
                'type', geometry_type,
                'coordinates', coordinates
            )::text
        )
    )
    LIMIT 1;
    
    RETURN suburb_id_result;
END;
$$ LANGUAGE plpgsql;

-- Create view for active sensors (last updated within 24 hours)
CREATE VIEW active_sensors AS
SELECT 
    s.*,
    CASE 
        WHEN s.last_updated > NOW() - INTERVAL '24 hours' THEN 'active'
        WHEN s.last_updated > NOW() - INTERVAL '7 days' THEN 'recent'
        ELSE 'inactive'
    END as activity_status
FROM on_street_sensors s;

-- Create view for sensor statistics by suburb
CREATE VIEW sensor_stats_by_suburb AS
SELECT 
    suburb_name,
    COUNT(*) as total_sensors,
    COUNT(CASE WHEN status_description = 'Present' THEN 1 END) as occupied_sensors,
    COUNT(CASE WHEN status_description = 'Unoccupied' THEN 1 END) as available_sensors,
    ROUND(
        COUNT(CASE WHEN status_description = 'Present' THEN 1 END)::DECIMAL / COUNT(*) * 100, 2
    ) as occupancy_rate
FROM on_street_sensors 
WHERE suburb_name IS NOT NULL
GROUP BY suburb_name
ORDER BY total_sensors DESC;

-- Insert sample data for testing (optional)
-- INSERT INTO on_street_sensors (kerbside_id, zone_number, status_description, last_updated, status_timestamp, latitude, longitude) VALUES
-- (51614, 7303, 'Unoccupied', '2025-03-25T11:44:37+11:00', '2025-03-25T11:09:20+11:00', -37.81620493158199, 144.96978894261684),
-- (17954, 7265, 'Present', '2025-03-25T11:44:37+11:00', '2025-03-25T10:56:53+11:00', -37.81019990197624, 144.97294577505386);

-- Grant permissions (adjust as needed)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON on_street_sensors TO your_user;
-- GRANT SELECT ON active_sensors TO your_user;
-- GRANT SELECT ON sensor_stats_by_suburb TO your_user;


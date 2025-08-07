-- Melbourne Parking Restrictions Database Schema
-- Stores pay-stay parking restrictions data from Melbourne Government Open Data

-- Drop existing table if exists
DROP TABLE IF EXISTS parking_restrictions CASCADE;

-- Create parking_restrictions table
CREATE TABLE parking_restrictions (
    id SERIAL PRIMARY KEY,
    pay_stay_zone INTEGER NOT NULL,                    -- Pay stay zone identifier (e.g., 30001003)
    day_of_week VARCHAR(2) NOT NULL,                   -- Day of week (1=Monday, 7=Sunday)
    day_of_week_name VARCHAR(20) NOT NULL,             -- Day name (Monday, Tuesday, etc.)
    start_time TIME NOT NULL,                          -- Start time (e.g., 07:30:00)
    end_time TIME NOT NULL,                            -- End time (e.g., 12:30:00)
    minimum_stay INTEGER DEFAULT 0,                    -- Minimum stay in minutes (0 = no minimum)
    maximum_stay INTEGER,                              -- Maximum stay in minutes (NULL = no limit)
    cost_per_hour INTEGER NOT NULL,                    -- Cost per hour in cents (e.g., 320 = $3.20)
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX idx_restrictions_zone ON parking_restrictions(pay_stay_zone);
CREATE INDEX idx_restrictions_day ON parking_restrictions(day_of_week);
CREATE INDEX idx_restrictions_time_range ON parking_restrictions(start_time, end_time);
CREATE INDEX idx_restrictions_cost ON parking_restrictions(cost_per_hour);
CREATE INDEX idx_restrictions_zone_day ON parking_restrictions(pay_stay_zone, day_of_week);

-- Create unique constraint to prevent duplicate restrictions for same zone/day
CREATE UNIQUE INDEX idx_restrictions_unique ON parking_restrictions(pay_stay_zone, day_of_week, start_time, end_time);

-- Create trigger to automatically update timestamp
CREATE TRIGGER update_restrictions_updated_at BEFORE UPDATE ON parking_restrictions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create views for common queries
-- View: Zone restrictions summary
CREATE VIEW zone_restrictions_summary AS
SELECT
    pay_stay_zone,
    COUNT(*) as total_restrictions,
    COUNT(DISTINCT day_of_week) as active_days,
    MIN(cost_per_hour) as min_cost_per_hour,
    MAX(cost_per_hour) as max_cost_per_hour,
    AVG(cost_per_hour)::INTEGER as avg_cost_per_hour,
    MIN(minimum_stay) as min_stay_minutes,
    MAX(maximum_stay) as max_stay_minutes
FROM parking_restrictions
GROUP BY pay_stay_zone
ORDER BY pay_stay_zone;

-- View: Daily restrictions summary
CREATE VIEW daily_restrictions_summary AS
SELECT
    day_of_week,
    day_of_week_name,
    COUNT(*) as total_restrictions,
    COUNT(DISTINCT pay_stay_zone) as active_zones,
    AVG(cost_per_hour)::INTEGER as avg_cost_per_hour,
    MIN(start_time) as earliest_start,
    MAX(end_time) as latest_end
FROM parking_restrictions
GROUP BY day_of_week, day_of_week_name
ORDER BY day_of_week;

-- View: Cost analysis by zone
CREATE VIEW zone_cost_analysis AS
SELECT
    pay_stay_zone,
    day_of_week_name,
    start_time,
    end_time,
    cost_per_hour,
    (cost_per_hour / 100.0) as cost_per_hour_dollars,
    minimum_stay,
    maximum_stay,
    CASE 
        WHEN maximum_stay IS NULL THEN 'No limit'
        ELSE maximum_stay::TEXT || ' minutes'
    END as max_stay_display
FROM parking_restrictions
ORDER BY pay_stay_zone, day_of_week, start_time;

-- Create functions for common operations
-- Function to get restrictions for a specific zone
CREATE OR REPLACE FUNCTION get_zone_restrictions(zone_id INTEGER)
RETURNS TABLE(
    day_of_week VARCHAR(2),
    day_name VARCHAR(20),
    start_time TIME,
    end_time TIME,
    cost_per_hour INTEGER,
    cost_dollars DECIMAL(5,2),
    min_stay INTEGER,
    max_stay INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        pr.day_of_week,
        pr.day_of_week_name,
        pr.start_time,
        pr.end_time,
        pr.cost_per_hour,
        (pr.cost_per_hour / 100.0)::DECIMAL(5,2),
        pr.minimum_stay,
        pr.maximum_stay
    FROM parking_restrictions pr
    WHERE pr.pay_stay_zone = zone_id
    ORDER BY pr.day_of_week, pr.start_time;
END;
$$ LANGUAGE plpgsql;

-- Function to get restrictions for a specific day
CREATE OR REPLACE FUNCTION get_day_restrictions(day_num VARCHAR(2))
RETURNS TABLE(
    zone_id INTEGER,
    day_name VARCHAR(20),
    start_time TIME,
    end_time TIME,
    cost_per_hour INTEGER,
    cost_dollars DECIMAL(5,2),
    min_stay INTEGER,
    max_stay INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        pr.pay_stay_zone,
        pr.day_of_week_name,
        pr.start_time,
        pr.end_time,
        pr.cost_per_hour,
        (pr.cost_per_hour / 100.0)::DECIMAL(5,2),
        pr.minimum_stay,
        pr.maximum_stay
    FROM parking_restrictions pr
    WHERE pr.day_of_week = day_num
    ORDER BY pr.pay_stay_zone, pr.start_time;
END;
$$ LANGUAGE plpgsql;

-- Function to find zones with restrictions at a specific time
CREATE OR REPLACE FUNCTION find_active_restrictions(check_time TIME, check_day VARCHAR(2))
RETURNS TABLE(
    zone_id INTEGER,
    day_name VARCHAR(20),
    start_time TIME,
    end_time TIME,
    cost_per_hour INTEGER,
    cost_dollars DECIMAL(5,2),
    min_stay INTEGER,
    max_stay INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        pr.pay_stay_zone,
        pr.day_of_week_name,
        pr.start_time,
        pr.end_time,
        pr.cost_per_hour,
        (pr.cost_per_hour / 100.0)::DECIMAL(5,2),
        pr.minimum_stay,
        pr.maximum_stay
    FROM parking_restrictions pr
    WHERE pr.day_of_week = check_day
      AND pr.start_time <= check_time
      AND pr.end_time >= check_time
    ORDER BY pr.cost_per_hour;
END;
$$ LANGUAGE plpgsql;

-- Example data queries that will be useful:

-- 1. Get all restrictions for a specific zone
-- SELECT * FROM get_zone_restrictions(30001003);

-- 2. Get all restrictions for a specific day
-- SELECT * FROM get_day_restrictions('2'); -- Tuesday

-- 3. Find active restrictions at a specific time
-- SELECT * FROM find_active_restrictions('09:00:00', '2'); -- 9 AM on Tuesday

-- 4. Get zone summary
-- SELECT * FROM zone_restrictions_summary WHERE pay_stay_zone = 30001003;

-- 5. Get daily summary
-- SELECT * FROM daily_restrictions_summary;

-- 6. Find most expensive zones
-- SELECT pay_stay_zone, MAX(cost_per_hour) as max_cost 
-- FROM parking_restrictions 
-- GROUP BY pay_stay_zone 
-- ORDER BY max_cost DESC 
-- LIMIT 10;

-- 7. Find zones with longest operating hours
-- SELECT pay_stay_zone, 
--        day_of_week_name,
--        start_time, 
--        end_time,
--        EXTRACT(EPOCH FROM (end_time - start_time))/3600 as hours_operating
-- FROM parking_restrictions 
-- ORDER BY hours_operating DESC 
-- LIMIT 10;

-- 8. Find free parking periods (cost_per_hour = 0)
-- SELECT * FROM parking_restrictions WHERE cost_per_hour = 0;

-- 9. Find zones with no maximum stay limit
-- SELECT * FROM parking_restrictions WHERE maximum_stay IS NULL;

-- 10. Get average cost by day of week
-- SELECT day_of_week_name, AVG(cost_per_hour)::INTEGER as avg_cost_cents
-- FROM parking_restrictions 
-- GROUP BY day_of_week_name, day_of_week 
-- ORDER BY day_of_week;

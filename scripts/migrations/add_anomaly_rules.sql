-- Migration: Add AnomalyRule and GlobalAnomalyConfig tables
-- Run this in the main_db PostgreSQL database

-- 1. Add severity column to anomalylog (if not exists)
ALTER TABLE anomalylog 
ADD COLUMN IF NOT EXISTS severity VARCHAR(20) DEFAULT 'warning';

-- 2. Update existing status values to new format
UPDATE anomalylog SET status = 'pending' WHERE status IN ('detected', 'analyzing');
UPDATE anomalylog SET status = 'dismissed' WHERE status IN ('resolved', 'rejected');

-- 3. Create AnomalyRule table
CREATE TABLE IF NOT EXISTS anomalyrule (
    id SERIAL PRIMARY KEY,
    pollutantid INTEGER NOT NULL REFERENCES pollutant(id) ON DELETE CASCADE,
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    warning_threshold FLOAT NOT NULL,
    critical_threshold FLOAT NOT NULL,
    sudden_change_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    sudden_change_percent FLOAT NOT NULL DEFAULT 50,
    sudden_change_minutes INTEGER NOT NULL DEFAULT 10,
    UNIQUE(pollutantid)
);

-- 4. Create GlobalAnomalyConfig table (singleton)
CREATE TABLE IF NOT EXISTS globalanomalyconfig (
    id SERIAL PRIMARY KEY,
    missing_data_timeout_minutes INTEGER NOT NULL DEFAULT 30
);

-- 5. Seed initial AnomalyRule data for each pollutant
INSERT INTO anomalyrule (pollutantid, warning_threshold, critical_threshold)
SELECT id, 
    CASE symbol
        WHEN 'PM2.5' THEN 25
        WHEN 'PM10' THEN 50
        WHEN 'NO2' THEN 40
        WHEN 'O3' THEN 100
        WHEN 'SO2' THEN 20
        ELSE 50
    END,
    CASE symbol
        WHEN 'PM2.5' THEN 50
        WHEN 'PM10' THEN 100
        WHEN 'NO2' THEN 80
        WHEN 'O3' THEN 180
        WHEN 'SO2' THEN 50
        ELSE 100
    END
FROM pollutant
ON CONFLICT (pollutantid) DO NOTHING;

-- 6. Seed GlobalAnomalyConfig singleton
INSERT INTO globalanomalyconfig (id, missing_data_timeout_minutes)
VALUES (1, 30)
ON CONFLICT (id) DO NOTHING;

-- Verify
SELECT 'AnomalyRules' as table_name, COUNT(*) as count FROM anomalyrule
UNION ALL
SELECT 'GlobalConfig' as table_name, COUNT(*) as count FROM globalanomalyconfig;

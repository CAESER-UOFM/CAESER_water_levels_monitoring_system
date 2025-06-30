# Database Schema Documentation

## Overview

The CAESER Water Levels Monitoring System uses SQLite as its primary database engine, designed for efficient water level data management, multi-user collaboration, and integration with AI/LLM systems.

## Database Architecture

### Core Design Principles
- **SQLite Foundation**: Lightweight, serverless, and highly compatible
- **Relational Structure**: Normalized design with proper foreign key relationships
- **Performance Optimized**: Strategic indexing and memory-adaptive configuration
- **AI-Ready**: Structured for natural language queries and machine learning integration
- **Cloud Synchronization**: Designed for Google Drive collaboration

### Performance Configuration
The system dynamically optimizes SQLite based on available system memory:

```sql
-- High Memory Systems (>16GB)
PRAGMA cache_size = -200000;  -- 200MB cache
PRAGMA mmap_size = 8589934592; -- 8GB memory mapping

-- Medium Memory Systems (8-16GB)  
PRAGMA cache_size = -100000;  -- 100MB cache
PRAGMA mmap_size = 4294967296; -- 4GB memory mapping

-- Low Memory Systems (<8GB)
PRAGMA cache_size = -10000;   -- 10MB cache
PRAGMA mmap_size = 1073741824; -- 1GB memory mapping
```

---

## Core Data Tables

### 1. Wells Table (`wells`)
**Primary entity** for monitoring well information and metadata.

```sql
CREATE TABLE wells (
    well_number TEXT PRIMARY KEY,
    cae_number TEXT,
    latitude REAL,
    longitude REAL,
    top_of_casing REAL,
    aquifer TEXT,
    min_distance_to_stream REAL,
    well_field TEXT,
    cluster TEXT,
    county TEXT,
    picture_path TEXT,
    data_source TEXT CHECK(data_source IN ('transducer', 'telemetry')),
    url TEXT,
    user_flag TEXT CHECK(user_flag IN ('unchecked', 'error', 'approved')),
    baro_status TEXT,
    level_status TEXT,
    parking_instructions TEXT,
    access_requirements TEXT,
    safety_notes TEXT,
    special_instructions TEXT
);
```

#### Key Fields Explanation
- **`well_number`**: Unique identifier for each monitoring well
- **`cae_number`**: CAESER-specific reference number
- **`latitude/longitude`**: Geographic coordinates (WGS84)
- **`top_of_casing`**: Elevation reference point for water level calculations
- **`data_source`**: Indicates whether data comes from installed transducers or telemetry
- **`user_flag`**: Quality control status (`unchecked`, `error`, `approved`)
- **`baro_status/level_status`**: Data processing status indicators

---

### 2. Water Level Readings (`water_level_readings`)
**Core time series data** from pressure transducers and calculated water levels.

```sql
CREATE TABLE water_level_readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    well_number TEXT NOT NULL,
    timestamp_utc TIMESTAMP NOT NULL,
    julian_timestamp REAL NOT NULL,
    pressure REAL,
    water_pressure REAL,
    water_level REAL,
    temperature REAL,
    serial_number TEXT,
    baro_flag TEXT,
    level_flag TEXT,
    source_xle_file TEXT,
    FOREIGN KEY (well_number) REFERENCES wells(well_number),
    FOREIGN KEY (serial_number) REFERENCES transducers(serial_number)
);

-- Performance Indexes
CREATE INDEX idx_water_readings_well_julian ON water_level_readings(well_number, julian_timestamp);
CREATE INDEX idx_water_readings_timestamp ON water_level_readings(timestamp_utc);
CREATE INDEX idx_water_readings_flags ON water_level_readings(baro_flag, level_flag);
```

#### Key Fields Explanation
- **`julian_timestamp`**: Optimized timestamp format for fast time-series queries
- **`pressure`**: Raw pressure reading from transducer (psi or kPa)
- **`water_pressure`**: Pressure after barometric compensation
- **`water_level`**: Calculated water surface elevation
- **`baro_flag/level_flag`**: Quality control indicators for data validation

---

### 3. Transducers Table (`transducers`)
**Equipment tracking** for pressure transducers and data loggers.

```sql
CREATE TABLE transducers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    serial_number TEXT UNIQUE NOT NULL,
    well_number TEXT,
    installation_date TIMESTAMP,
    end_date TIMESTAMP,
    notes TEXT,
    FOREIGN KEY (well_number) REFERENCES wells(well_number)
);
```

---

### 4. Barometric Data System

#### Barologgers (`barologgers`)
```sql
CREATE TABLE barologgers (
    serial_number TEXT PRIMARY KEY,
    location_description TEXT,
    installation_date TIMESTAMP,
    status TEXT CHECK(status IN ('active', 'inactive'))
);
```

#### Barometric Readings (`barometric_readings`)
```sql
CREATE TABLE barometric_readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    serial_number TEXT NOT NULL,
    timestamp_utc TIMESTAMP NOT NULL,
    julian_timestamp REAL NOT NULL,
    pressure REAL NOT NULL,
    temperature REAL,
    quality_flag TEXT,
    FOREIGN KEY (serial_number) REFERENCES barologgers(serial_number)
);

CREATE INDEX idx_baro_readings_serial_julian ON barometric_readings(serial_number, julian_timestamp);
```

#### Master Barometric Data (`master_baro_readings`)
**Composite atmospheric pressure** data from multiple barologgers.

```sql
CREATE TABLE master_baro_readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp_utc TIMESTAMP NOT NULL,
    julian_timestamp REAL NOT NULL,
    pressure REAL NOT NULL,
    temperature REAL,
    source_barologgers TEXT, -- JSON array of contributing loggers
    processing_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX idx_master_baro_timestamp ON master_baro_readings(julian_timestamp);
```

---

### 5. Manual Measurements (`manual_level_readings`)
**Field measurements** taken with water level meters and tapes.

```sql
CREATE TABLE manual_level_readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    well_number TEXT NOT NULL,
    measurement_date_utc TIMESTAMP NOT NULL,
    dtw_avg REAL, -- Average depth to water
    dtw_1 REAL,   -- First measurement
    dtw_2 REAL,   -- Second measurement  
    tape_error REAL, -- Instrument correction
    water_level REAL, -- Calculated elevation
    data_source TEXT,
    collected_by TEXT,
    is_dry BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (well_number) REFERENCES wells(well_number)
);

CREATE INDEX idx_manual_readings_well_date ON manual_level_readings(well_number, measurement_date_utc);
```

---

### 6. Telemetry Data (`telemetry_level_readings`)
**Real-time data** from telemetry monitoring systems.

```sql
CREATE TABLE telemetry_level_readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    well_number TEXT NOT NULL,
    timestamp_utc TIMESTAMP NOT NULL,
    julian_timestamp REAL NOT NULL,
    water_level REAL,
    temperature REAL,
    dtw REAL, -- Depth to water
    FOREIGN KEY (well_number) REFERENCES wells(well_number)
);

CREATE INDEX idx_telemetry_well_julian ON telemetry_level_readings(well_number, julian_timestamp);
```

---

## User Management System

### Users Table (`users`)
**Authentication and access control** for multi-user environments.

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    salt TEXT NOT NULL,
    display_name TEXT,
    role TEXT CHECK(role IN ('admin', 'user', 'guest')),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);
```

---

## Recharge Calculation Tables

### RISE Method Results (`rise_calculations`)
```sql
CREATE TABLE rise_calculations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    well_number TEXT NOT NULL,
    calculation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    parameters TEXT, -- JSON configuration
    events_data TEXT, -- JSON results
    yearly_summary TEXT, -- JSON summary
    total_recharge REAL,
    annual_rate REAL,
    FOREIGN KEY (well_number) REFERENCES wells(well_number)
);
```

### MRC Method Results (`mrc_calculations`)
```sql
CREATE TABLE mrc_calculations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    well_number TEXT NOT NULL,
    calculation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    parameters TEXT, -- JSON configuration
    recession_data TEXT, -- JSON recession analysis
    yearly_summary TEXT, -- JSON summary
    total_recharge REAL,
    annual_rate REAL,
    FOREIGN KEY (well_number) REFERENCES wells(well_number)
);
```

### ERC Method Results (`erc_calculations`)
```sql
CREATE TABLE erc_calculations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    well_number TEXT NOT NULL,
    calculation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    parameters TEXT, -- JSON configuration
    curve_data TEXT, -- JSON curve analysis
    yearly_summary TEXT, -- JSON summary
    total_recharge REAL,
    annual_rate REAL,
    FOREIGN KEY (well_number) REFERENCES wells(well_number)
);
```

---

## Data Relationships and Integrity

### Foreign Key Relationships
```
wells (1) ←→ (∞) water_level_readings
wells (1) ←→ (∞) transducers  
wells (1) ←→ (∞) manual_level_readings
wells (1) ←→ (∞) telemetry_level_readings
wells (1) ←→ (∞) rise_calculations
wells (1) ←→ (∞) mrc_calculations
wells (1) ←→ (∞) erc_calculations

barologgers (1) ←→ (∞) barometric_readings
transducers (1) ←→ (∞) water_level_readings
```

### Data Integrity Constraints
- **Temporal Consistency**: Timestamps must be valid and properly ordered
- **Geographic Validity**: Coordinates must be within reasonable ranges
- **Quality Flags**: Standardized enumeration values for data quality
- **Reference Integrity**: All foreign keys must reference existing records

---

## Performance Optimization

### Strategic Indexing
```sql
-- Time-series query optimization
CREATE INDEX idx_water_readings_well_julian ON water_level_readings(well_number, julian_timestamp);
CREATE INDEX idx_baro_readings_serial_julian ON barometric_readings(serial_number, julian_timestamp);

-- Geographic queries
CREATE INDEX idx_wells_coordinates ON wells(latitude, longitude);

-- Quality control filtering
CREATE INDEX idx_water_readings_flags ON water_level_readings(baro_flag, level_flag);
CREATE INDEX idx_wells_user_flag ON wells(user_flag);

-- User authentication
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_active ON users(is_active);
```

### Query Optimization Patterns
```sql
-- Efficient time-series queries using Julian timestamps
SELECT * FROM water_level_readings 
WHERE well_number = 'MW-001' 
  AND julian_timestamp BETWEEN 2459000 AND 2459365
ORDER BY julian_timestamp;

-- Multi-table joins with proper indexing
SELECT w.well_number, w.latitude, w.longitude, 
       COUNT(wlr.id) as reading_count
FROM wells w
LEFT JOIN water_level_readings wlr ON w.well_number = wlr.well_number
WHERE w.user_flag = 'approved'
GROUP BY w.well_number;
```

---

## AI and LLM Integration Features

### Natural Language Query Support
The database structure is optimized for AI/LLM integration:

- **Descriptive Field Names**: Human-readable column names for natural language processing
- **Standardized Enumerations**: Consistent vocabulary for quality flags and status indicators
- **JSON Data Storage**: Flexible storage for complex analysis parameters and results
- **Comprehensive Metadata**: Rich contextual information for intelligent queries

### Example AI Query Patterns
```sql
-- Wells with recent data issues
SELECT well_number, COUNT(*) as error_count
FROM water_level_readings 
WHERE level_flag = 'error' 
  AND timestamp_utc > datetime('now', '-30 days')
GROUP BY well_number
ORDER BY error_count DESC;

-- Seasonal recharge patterns
SELECT strftime('%m', timestamp_utc) as month,
       AVG(water_level) as avg_level
FROM water_level_readings wlr
JOIN wells w ON wlr.well_number = w.well_number
WHERE w.aquifer = 'Memphis Aquifer'
GROUP BY month;
```

---

## Data Migration and Versioning

### Schema Evolution
```sql
-- Example migration: Adding Julian timestamps
ALTER TABLE water_level_readings ADD COLUMN julian_timestamp REAL;

-- Update existing records
UPDATE water_level_readings 
SET julian_timestamp = julianday(timestamp_utc);

-- Add index for performance
CREATE INDEX idx_water_readings_julian ON water_level_readings(julian_timestamp);
```

### Backup and Recovery
- **Automated Backups**: Regular SQLite database file backups
- **Cloud Synchronization**: Google Drive integration for collaborative environments
- **Version Control**: Draft system for handling concurrent edits
- **Recovery Procedures**: Rollback capabilities for data protection

---

**Next Steps**: Continue to [Data Processing](data_processing.md) to understand how data flows through the system and transforms from raw sensor readings to analytical results.
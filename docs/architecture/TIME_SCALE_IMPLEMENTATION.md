# Time Scale Feature Implementation Summary

## Overview
Added a `time_scale` query parameter to FastAPI endpoints that deliver time-series data. The parameter accepts enum values: `weekly`, `monthly`, and `yearly`, allowing clients to aggregate data at different time granularities.

## Files Created

### 1. `/src/admin_api/reports/enums.py`
- **Purpose**: Central location for report-related enums
- **Content**: `TimeScaleEnum` with values: WEEKLY, MONTHLY, YEARLY

### 2. `/src/admin_api/reports/timeranges.py`
- **Purpose**: Utility functions for generating date ranges at different time scales
- **Functions**:
  - `weekly_range()`: Generates first day (Monday) of each week between date range
  - `yearly_range()`: Generates first day of each year between date range

## Files Modified

### Sales Report
**File**: `/src/admin_api/reports/sales/`

1. **serializers.py**
   - Added `time_scale` query parameter to `SalesReportQuery`
   - Default: `TimeScaleEnum.WEEKLY`
   - Supported values: weekly, monthly, yearly

2. **router.py**
   - Updated `/data` endpoint to pass `time_scale` to service

3. **service.py**
   - Added imports for `TimeScaleEnum` and `weekly_range`, `yearly_range`
   - Updated `get_report()` method signature with `time_scale` parameter (default: WEEKLY)
   - Added routing logic in `get_report()` to call appropriate time-scale method
   - Added two new methods:
     - `_weekly_sales()`: Aggregates sales data by week
     - `_yearly_sales()`: Aggregates sales data by year

### Bookings Report
**File**: `/src/admin_api/reports/bookings/`

1. **serializers.py**
   - Added `time_scale` query parameter to `BookingReportQuery`
   - Default: `TimeScaleEnum.WEEKLY`
   - Supported values: weekly, monthly, yearly

2. **router.py**
   - Updated `/data` endpoint to pass `time_scale` to service

3. **domainmodel.py**
   - Added two new date generation functions:
     - `weekly_points()`: Generates week start dates (Monday)
     - `yearly_points()`: Generates year start dates

4. **service.py**
   - Added imports for `TimeScaleEnum`, `weekly_points`, `yearly_points`
   - Updated `get_report()` method signature with `time_scale` parameter (default: WEEKLY)
   - Enhanced `DAY` group_by logic to respect `time_scale` parameter:
     - When `time_scale=MONTHLY`: Uses month granularity
     - When `time_scale=YEARLY`: Uses year granularity
     - Default: Uses weekly granularity
   - Added two new methods:
     - `_week_rows()`: Generates booking report rows by week (labeled as W# YYYY)
     - `_year_rows()`: Generates booking report rows by year

### Finance Report
**File**: `/src/admin_api/reports/finance/`

1. **serializers.py**
   - Added `time_scale` query parameter to `FinanceReportQuery`
   - Default: `TimeScaleEnum.WEEKLY`
   - Supported values: weekly, monthly, yearly

2. **router.py**
   - Updated `/data` endpoint to pass `time_scale` to service

3. **domainmodel.py**
   - Added two new trend date generation functions:
     - `finance_trend_weeks()`: Generates week start dates (Monday) for trend data
     - `finance_trend_years()`: Generates year start dates for trend data

4. **service.py**
   - Added imports for `TimeScaleEnum`, `finance_trend_weeks`, `finance_trend_years`
   - Updated `get_report()` method signature with `time_scale` parameter (default: WEEKLY)
   - Enhanced trend data generation logic to route based on `time_scale`:
     - When `time_scale=MONTHLY`: Uses monthly aggregation (12 points)
     - When `time_scale=YEARLY`: Uses yearly aggregation
     - Default: Uses weekly aggregation

### Operations Report
**File**: `/src/admin_api/reports/operations/`

1. **serializers.py**
   - Added `time_scale` query parameter to `OperationsReportQuery`
   - Default: `TimeScaleEnum.WEEKLY`
   - Supported values: weekly, monthly, yearly

2. **router.py**
   - Updated `/data` endpoint to pass `time_scale` to service

3. **service.py**
   - Added import for `TimeScaleEnum`
   - Updated `get_report()` method signature to accept `time_scale` parameter (default: WEEKLY)
   - Currently accepts parameter for API consistency (future aggregation support)

## API Changes

### Sales Report
- **Endpoint**: `POST /reports/sales/data`
- **New Query Parameter**: `timeScale` (query param alias)
- **Values**: `weekly`, `monthly`, `yearly`
- **Default**: `weekly`
- **Example**: `/reports/sales/data?reportType=daily_sales&timeScale=monthly`

### Bookings Report
- **Endpoint**: `POST /reports/bookings/data`
- **New Query Parameter**: `timeScale` (query param alias)
- **Values**: `weekly`, `monthly`, `yearly`
- **Default**: `weekly`
- **Note**: Works in conjunction with `groupBy` parameter. When `groupBy=day`, `timeScale` determines aggregation granularity
- **Example**: `/reports/bookings/data?reportType=booking_overview&groupBy=day&timeScale=monthly`

### Finance Report
- **Endpoint**: `POST /reports/finance/data`
- **New Query Parameter**: `timeScale` (query param alias)
- **Values**: `weekly`, `monthly`, `yearly`
- **Default**: `weekly`
- **Example**: `/reports/finance/data?timeScale=yearly`

### Operations Report
- **Endpoint**: `POST /reports/operations/data`
- **New Query Parameter**: `timeScale` (query param alias)
- **Values**: `weekly`, `monthly`, `yearly`
- **Default**: `weekly`
- **Example**: `/reports/operations/data?timeScale=monthly`

## Technical Details

### Time Scale Logic
- **WEEKLY**: Returns data points aggregated by week (Monday as start date)
- **MONTHLY**: Aggregates data by calendar month (1st day of month)
- **YEARLY**: Aggregates data by calendar year (January 1st)

### Backward Compatibility
- All changes are backward compatible
- Default value is `weekly` to provide reasonable time granularity
- Existing API calls without `timeScale` parameter will continue to work with weekly aggregation

### Implementation Pattern
Each report service implements time-scale support consistently:
1. Accept `time_scale` parameter in the service method
2. Route to appropriate internal method based on `time_scale` value
3. Generate appropriate date ranges using dedicated functions
4. Maintain existing mock data generation logic with proper timestamps
5. Format labels appropriately (e.g., "W45 2024" for week, "2024" for year)

## Files NOT Modified
- `luxtj` module APIs (as per requirements)
- Customers report (no time-series data in response)
- Partners report (no time-series data in response)
- Marketing report (no time-series data in response)

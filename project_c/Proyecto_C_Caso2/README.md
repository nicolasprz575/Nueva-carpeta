# Proyecto C Caso 2 - National Logistics with Strategic Refueling

## Project Context

**LogistiCo National Logistics Division** manages long-haul transport of cargo from ports to municipalities across Colombia. This case features:
- **Long-distance routing** (hundreds of kilometers)
- **Strategic refueling decisions** at stations with variable fuel prices
- **Tractomula fleet** (heavy-duty trucks)
- **Single origin** (Port of Barranquilla)

**Case Level**: Simplified project-specific (25% of implementation grade)

## Data Files

### 1. `clients.csv`
Municipalities/delivery destinations across Colombia.

| Column | Type | Unit | Description |
|--------|------|------|-------------|
| ClientID | Integer | - | Numeric client/municipality identifier |
| StandardizedID | String | - | Standardized ID (C001, C002, ...) for verification |
| City/Municipality | String | - | Municipality name (for readability) |
| LocationID | Integer | - | Unified location identifier |
| Demand | Float | kg | Cargo quantity required |

### 2. `vehicles.csv`
Tractomula (tractor-trailer) fleet.

| Column | Type | Unit | Description |
|--------|------|------|-------------|
| VehicleID | Integer | - | Numeric vehicle identifier |
| StandardizedID | String | - | Standardized ID (V001, V002, ...) |
| Capacity | Float | kg | Maximum cargo capacity (typically 23,500-35,000 kg) |
| Range | Float | km | Maximum travel distance on full fuel tank |

### 3. `depots.csv`
Port of origin (single depot).

| Column | Type | Unit | Description |
|--------|------|------|-------------|
| DepotID | Integer | - | Depot identifier (1) |
| StandardizedID | String | - | Standardized ID (CD01) |
| LocationID | Integer | - | Unified location identifier |
| Latitude | Float | degrees | Port latitude |
| Longitude | Float | degrees | Port longitude |

### 4. `stations.csv` ⭐ NEW
Refueling stations with variable prices.

| Column | Type | Unit | Description |
|--------|------|------|-------------|
| EstationID | Integer | - | Numeric station identifier |
| StandardizedID | String | - | Standardized ID (E001, E002, ...) |
| LocationID | Integer | - | Unified location identifier (100+) |
| Latitude | Float | degrees | Station latitude |
| Longitude | Float | degrees | Station longitude |
| **FuelCost** | Float | COP/gallon | **Diesel price at this station** |

**KEY**: Fuel prices VARY by station - strategic refueling is critical for cost optimization!

## Cost Parameters

See `parameters_national.csv`:

- **C_fixed**: 80,000 COP/vehicle (tractomula activation)
- **C_dist**: 4,500 COP/km (long-haul maintenance)
- **C_time**: 9,000 COP/hour (specialized driver)
- **Fuel efficiency**: 8-10 km/gallon (full load), use 9 km/gal typical
- **Fuel prices**: VARIABLE - see stations.csv FuelCost column

### Objective Function:
```
min Z = Σ(C_fixed × y_v) + Σ(C_dist × d_v) + Σ(C_time × t_v) + C_fuel

Where:
- C_fuel = Σ(gallons refueled at each station × station price)
- Refueling decisions are OPTIMIZATION VARIABLES
```

## Project-Specific Constraints

1. **Strategic Refueling**:
   - Vehicles start with full tank at port
   - Can refuel at any station along route
   - Must not run out of fuel between any two locations
   - Decide: WHERE to refuel and HOW MUCH

2. **Single Origin**: All routes start from port (CD01)

3. **Fuel Management**:
   - Track fuel level throughout route
   - Fuel consumed = distance / efficiency
   - Range constraint enforced between refueling

4. **Coverage**: All municipalities visited, cargo demands satisfied

## Verification File Format

Create `verificacion_caso2.csv`:

```csv
VehicleId,LoadCap,FuelCap,RouteSequence,Municipalities,DemandSatisfied,InitLoad,InitFuel,RefuelStops,RefuelAmounts,Distance,Time,FuelCost,TotalCost
V001,20000,200,CD01-C003-E002-C007-C012-CD01,3,5200-0-7800-6500,19500,180,1,150,380.5,320.2,175000,680000
```

### Key Columns:
- **RouteSequence**: Includes both municipalities (C###) AND stations (E###)
- **DemandSatisfied**: Use 0 for stations (they're not delivery points)
- **RefuelStops**: Number of refueling events
- **RefuelAmounts**: Gallons refueled at each station, separated by hyphens
- **FuelCost**: Total spent on fuel (sum of refueling costs)

## Strategic Refueling Example

Route: Port → Bogotá (300 km) → Station A → Medellín (250 km) → Port

- Start with 200 gallons
- Travel to Bogotá: 300 km / 9 km/gal = 33.3 gallons used, 166.7 remaining
- Refuel at Station A: Add 100 gallons → 266.7 gallons
- Travel to Medellín: 250 km / 9 km/gal = 27.8 gallons, 238.9 remaining
- Return to port: Enough fuel remains

**Optimization**: Choose cheaper stations, avoid expensive ones if possible!

## Deliverables for Caso 2

1. ✓ Correct refueling model with fuel tracking (15%)
2. ✓ Feasible solution (no fuel run-outs) (7%)
3. ✓ Basic visualization showing refueling points (3%)

## Visualization Requirements

**Required**:
- Map of national routes with refueling stations marked
- Fuel price heatmap (which stations are cheaper?)
- Route diagram showing where each vehicle refuels

**Recommended**:
- Fuel level evolution chart per vehicle
- Cost comparison: optimal refueling vs. refueling everywhere

## Important Notes

- **Fuel prices vary** - this is the main optimization lever
- Station visits are OPTIONAL - only include if refueling
- Don't confuse stations (E###) with municipalities (C###)
- Tractomulas use DIESEL, not gasoline (but calculations are same)
- Use full-load efficiency (8-10 km/gal) as specified in main.tex

## ID Standardization

Use StandardizedID in verification files:
- Port: CD01
- Municipalities: C001, C002, C003, ...
- Stations: E001, E002, E003, ...
- Vehicles: V001, V002, V003, ...

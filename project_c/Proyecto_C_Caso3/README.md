# Proyecto C Caso 3 - National Logistics with Refueling, Tolls & Weight Restrictions

## Project Context

**Advanced realistic case** combining ALL national logistics complexities:
- **Strategic refueling** with variable fuel prices
- **Toll system** with variable rates (base + weight-dependent)
- **Municipal weight restrictions** (some municipalities limit truck weight)
- **Long-haul optimization** across Colombia

**Case Level**: Advanced realistic (20% + bonus eligible up to 20%)

## What's New in Caso 3?

1. **Toll System**: Roads have tolls with costs = BaseRate + (Weight × RatePerTon)
2. **Weight Restrictions**: Some municipalities have MaxWeight limits
3. **Combined Optimization**: Route + refuel + toll avoidance + weight compliance

## Data Files

Same as Caso 2 PLUS:

### 5. `tolls.csv` ⭐ NEW
Toll plazas with variable pricing.

| Column | Type | Unit | Description |
|--------|------|------|-------------|
| TollID | Integer | - | Numeric toll identifier |
| StandardizedID | String | - | Standardized ID (P001, P002, ...) |
| LocationID | Integer | - | Unified location identifier (200+) |
| ClientID | Integer | - | Associated municipality/client ID |
| TollName | String | - | Toll plaza name |
| **BaseRate** | Float | COP | **Fixed toll cost** |
| **RatePerTon** | Float | COP/ton | **Additional cost per ton of cargo** |

**Toll Cost Formula**: `TotalTollCost = BaseRate + (VehicleWeight_in_tons × RatePerTon)`

### clients.csv Additional Column:
- **MaxWeight**: Weight limit in kg (N/A if no restriction)

## Cost Parameters

Same as Caso 2 (`parameters_national.csv`) PLUS toll costs from tolls.csv.

### Enhanced Objective Function:
```
min Z = Σ(C_fixed × y_v) + Σ(C_dist × d_v) + Σ(C_time × t_v) + C_fuel + C_tolls

Where:
- C_tolls = Σ(BaseRate_p + Weight_v_at_p × RatePerTon_p) for all tolls p traversed
- Weight varies by route position (decreases as cargo delivered)
```

## Project-Specific Constraints

All Caso 2 constraints PLUS:

1. **Toll Avoidance/Optimization**:
   - Tolls located on specific road segments
   - Can potentially route around expensive tolls
   - Weight-dependent costs incentivize early deliveries (lighter = cheaper tolls)

2. **Municipal Weight Restrictions**:
   - Some municipalities have MaxWeight limits
   - Vehicle weight = vehicle_empty_weight + current_cargo
   - Must respect: `vehicle_weight ≤ MaxWeight` when entering municipality
   - Infeasible to visit restricted municipality if overweight

3. **Dynamic Weight Tracking**:
   - Vehicle weight decreases as deliveries made
   - Toll costs depend on weight at time of passage
   - Order of deliveries affects toll costs!

## Verification File Format

Create `verificacion_caso3.csv`:

```csv
VehicleId,LoadCap,FuelCap,RouteSeq,Municipalities,Demand,InitLoad,InitFuel,RefuelStops,RefuelAmounts,TollsVisited,TollCosts,VehicleWeights,Distance,Time,FuelCost,TollCost,TotalCost
V001,20000,200,CD01-C003-E002-P001-C007-P003-C012-CD01,3,5200-0-0-7800-0-6500,19500,180,1,150,2,85000-92000,19500-14300-6500,420.5,360.2,175000,177000,980000
```

### New Columns for Caso 3:
- **TollsVisited**: Number of toll plazas passed
- **TollCosts**: Cost paid at each toll (in COP), separated by hyphens
- **VehicleWeights**: Vehicle weight (kg) when entering each MUNICIPALITY, separated by hyphens
- **TollCost**: Total toll expenditure
- **TotalCost**: Sum of ALL cost components

**Note**: RouteSeq includes municipalities (C###), stations (E###), AND tolls (P###)

## Weight Calculation Example

Tractomula capacity: 25,000 kg, empty weight: 8,000 kg

Route: Port → Bogotá (deliver 6,000 kg) → Toll A → Medellín (deliver 4,000 kg) → Toll B → Return

- At Bogotá entry: 8,000 + 10,000 = 18,000 kg
- At Toll A: 8,000 + 4,000 = 12,000 kg (after Bogotá delivery)
  - Toll cost = 50,000 + (12 tons × 800) = 59,600 COP
- At Medellín entry: 8,000 + 4,000 = 12,000 kg
- At Toll B: 8,000 kg (empty after all deliveries)
  - Toll cost = 50,000 + (8 tons × 800) = 56,400 COP

## Strategic Considerations

1. **Delivery Order Matters**: Deliver heavy cargo early to reduce toll costs
2. **Route Selection**: May avoid expensive tolls if detour is worthwhile
3. **Weight Restrictions**: Plan routes to comply with municipal limits
4. **Combined Optimization**: Balance fuel costs, toll costs, distance, time

## Deliverables for Caso 3

Same as Caso 2 PLUS:

1. **Toll Impact Analysis**:
   - Total toll costs vs. other cost components
   - Toll avoidance strategies (if any)
   - Weight-based toll optimization results

2. **Weight Compliance Report**:
   - Which municipalities have restrictions
   - How routes adapt to restrictions
   - Impact on route structure

3. **Sensitivity Analysis**:
   - ±20% fuel price changes
   - Impact of removing/adding tolls
   - Effect of tighter weight restrictions

4. **Business Insights**:
   - Where should LogistiCo negotiate fuel contracts?
   - Which toll roads provide best value?
   - How do weight restrictions affect operations?

## Visualization Requirements

All Caso 2 requirements PLUS:
- Toll locations and costs on map
- Weight evolution diagram per vehicle
- Cost breakdown pie chart (fixed, distance, time, fuel, tolls)
- Municipality weight restriction heatmap

## Competitive Bonus Strategy

Focus on:
- **Integrated optimization**: Don't optimize fuel/tolls separately
- **Innovative approaches**: Novel formulations for this complex problem
- **Deep analysis**: Show trade-offs between competing objectives
- **Actionable insights**: Real recommendations for LogistiCo

## Important Notes

- Toll costs are HIGHLY variable (depend on weight)
- Early deliveries = lighter vehicle = cheaper tolls
- Weight restrictions can force specific route structures
- This is the most complex CVRP variant - start simple, add complexity incrementally
- Document all assumptions and modeling decisions

## ID Standardization

Use StandardizedID in verification files:
- Port: CD01
- Municipalities: C001, C002, C003, ...
- Stations: E001, E002, E003, ...
- Tolls: P001, P002, P003, ...
- Vehicles: V001, V002, V003, ...

## Solving Tips

1. Test with Caso 2 first (ignore tolls/weights initially)
2. Add tolls with constant weight assumption
3. Finally, add dynamic weight tracking
4. Use good initial solutions (heuristics) if MIP struggles
5. Document computational challenges encountered

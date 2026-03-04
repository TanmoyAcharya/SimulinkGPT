# Simulink Model Debugging Guide

## Common Simulink Errors and Solutions

### 1. Algebraic Loop Errors

**Error:** "Algebraic loop detected involving..."

**Cause:** Direct feedthrough from output to input of the same block without any time delay.

**Solutions:**
- Add a Unit Delay block to break the loop
- Use a Memory block instead of Unit Delay for discrete systems
- Restructure the model to eliminate direct feedthrough
- Enable "algebraic loop icon" diagnostic to see loop path

**Example:**
```
If you have: Signal -> Gain -> (same signal)
Solution: Add Unit Delay after the Gain block
```

### 2. Signal Dimension Mismatch

**Error:** "Input port dimensions mismatch" or "Dimension 1 is not consistent"

**Cause:** Connecting signals with different widths or data types.

**Solutions:**
- Check signal dimensions using "Display > Signals > Signal Dimensions"
- Use Reshape block to change signal dimensions
- Ensure consistent data types using Data Type Conversion blocks
- Check for implicit signal resolution in Mux/Demux blocks

### 3. Solver Configuration Issues

**Error:** "Simulation timing error" or "Invalid solver settings"

**Common Solver Problems:**
- Variable-step solver with discrete states
- Stiff system solved with non-stiff solver
- Step size too large for fast dynamics

**Solutions:**
- For primarily discrete systems: Use fixed-step solver
- For stiff systems: Use ode15s or ode23s
- For continuous systems: Use ode45 for non-stiff
- Set "Refine factor" to increase output points

### 4. Bus Signal Issues

**Error:** "Bus signal must be virtual except..." or "Invalid bus object"

**Solutions:**
- Use Bus Creator to create bus signals
- Use Bus Selector to extract elements
- Define Bus objects for non-virtual buses
- Ensure matching bus hierarchies

### 5. Model Reference Errors

**Error:** "Model reference diagram update failed"

**Solutions:**
- Rebuild referenced models: `slbuild('modelname')`
- Check model update差了 (callback functions)
- Ensure all referenced models are on MATLAB path
- Clear model workspace: `clear all; bdclose all;`

## Debugging Techniques

### Using Simulation Pause Points
1. Set breakpoints in Stateflow charts
2. Use "Stop Time" to pause at specific times
3. Enable "Pause at simulation start"

### Signal Builder Inspection
- Right-click signal > "Log Signals"
- Use Simulation Data Inspector to view logged signals
- Enable "Signal & Scope Manager" for signal monitoring

### Diagnostic Viewer
- View > Simulation Diagnostics
- Filter by severity (Error, Warning, Info)
- Use "Open" to highlight source blocks

### Performance Profiling
1. Enable "Performance Advisor" from Analysis menu
2. Use `sim('model', 'Profile', 'on')`
3. Check "Model Configuration Parameters > Performance"

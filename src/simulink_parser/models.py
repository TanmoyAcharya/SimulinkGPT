"""
Data models for Simulink model representation.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum


class BlockType(Enum):
    """Common Simulink block types."""
    SOURCE = "source"
    SINK = "sink"
    MATH = "math"
    LOGIC = "logic"
    SIGNAL = "signal"
    SUBSYSTEM = "subsystem"
    SCOPE = "scope"
    GAIN = "gain"
    SUM = "sum"
    INTEGRATOR = "integrator"
    DERIVATIVE = "derivative"
    DELAY = "delay"
    MUX = "mux"
    DEMUX = "demux"
    SWITCH = "switch"
    UNKNOWN = "unknown"


@dataclass
class SimulinkBlock:
    """Represents a single block in a Simulink model."""
    name: str
    block_type: str
    path: str  # Full path in model hierarchy
    parameters: Dict[str, Any] = field(default_factory=dict)
    ports: Dict[str, List[str]] = field(default_factory=dict)  # input/output ports
    position: Optional[List[int]] = None  # [x, y, width, height]
    parent: Optional[str] = None  # Parent subsystem path
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "name": self.name,
            "block_type": self.block_type,
            "path": self.path,
            "parameters": self.parameters,
            "ports": self.ports,
            "position": self.position,
            "parent": self.parent
        }
    
    def get_type_category(self) -> BlockType:
        """Categorize the block type."""
        type_lower = self.block_type.lower()
        
        if any(t in type_lower for t in ["in", "out", "constant", "signal generator"]):
            return BlockType.SOURCE
        elif any(t in type_lower for t in ["scope", "display", "to workspace", "sink"]):
            return BlockType.SINK
        elif any(t in type_lower for t in ["gain", "product", "divide"]):
            return BlockType.GAIN
        elif any(t in type_lower for t in ["sum", "add", "subtract"]):
            return BlockType.SUM
        elif any(t in type_lower for t in ["integrator", "derivative", "delay"]):
            return BlockType.INTEGRATOR
        elif any(t in type_lower for t in ["mux", "demux", "selector"]):
            return BlockType.SIGNAL
        elif "subsystem" in type_lower:
            return BlockType.SUBSYSTEM
        elif any(t in type_lower for t in ["math", "abs", "sqrt", "log", "exp"]):
            return BlockType.MATH
        elif any(t in type_lower for t in ["logic", "and", "or", "not", "relational"]):
            return BlockType.LOGIC
        elif any(t in type_lower for t in ["switch", "if", "action port"]):
            return BlockType.SWITCH
        else:
            return BlockType.UNKNOWN


@dataclass
class SimulinkSignal:
    """Represents a signal connection between blocks."""
    name: Optional[str]
    source_block: str  # Source block path
    source_port: str   # Source port (e.g., "1", "L")
    target_block: str  # Target block path
    target_port: str   # Target port
    signal_width: Optional[int] = None  # Signal dimensions
    data_type: Optional[str] = None    # e.g., "double", "single"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "name": self.name,
            "source_block": self.source_block,
            "source_port": self.source_port,
            "target_block": self.target_block,
            "target_port": self.target_port,
            "signal_width": self.signal_width,
            "data_type": self.data_type
        }


@dataclass
class SimulinkModel:
    """Complete representation of a Simulink model."""
    name: str
    file_path: str
    blocks: List[SimulinkBlock] = field(default_factory=list)
    signals: List[SimulinkSignal] = field(default_factory=list)
    subsystems: List[str] = field(default_factory=list)  # Subsystem paths
    parameters: Dict[str, Any] = field(default_factory=dict)  # Model parameters
    configuration: Dict[str, Any] = field(default_factory=dict)  # Solver, etc.
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "name": self.name,
            "file_path": self.file_path,
            "blocks": [b.to_dict() for b in self.blocks],
            "signals": [s.to_dict() for s in self.signals],
            "subsystems": self.subsystems,
            "parameters": self.parameters,
            "configuration": self.configuration
        }
    
    def to_text_summary(self) -> str:
        """Generate a detailed text summary of the model for LLM context."""
        lines = [
            f"Simulink Model: {self.name}",
            f"File: {self.file_path}",
            f"Total Blocks: {len(self.blocks)}",
            f"Total Signals: {len(self.signals)}",
            f"Subsystems: {len(self.subsystems)}",
            ""
        ]
        
        # Group blocks by type
        blocks_by_type: Dict[str, List[SimulinkBlock]] = {}
        for block in self.blocks:
            # Use actual block type for more accurate grouping
            category = block.block_type if block.block_type else 'unknown'
            if category not in blocks_by_type:
                blocks_by_type[category] = []
            blocks_by_type[category].append(block)
        
        lines.append("=== BLOCKS BY TYPE ===")
        for category, blocks in sorted(blocks_by_type.items()):
            lines.append(f"\n{category.upper()} ({len(blocks)} blocks):")
            for block in blocks[:20]:  # Limit to first 20 per type
                lines.append(f"  - {block.name}")
                # Include key parameters
                if block.parameters:
                    key_params = list(block.parameters.keys())[:5]
                    params_str = ", ".join(f"{k}={block.parameters[k][:50]}" for k in key_params if block.parameters.get(k))
                    if params_str:
                        lines.append(f"    Params: {params_str}")
                # Include parent subsystem
                if block.parent:
                    lines.append(f"    Parent: {block.parent}")
            if len(blocks) > 20:
                lines.append(f"  ... and {len(blocks) - 20} more")
        
        if self.subsystems:
            lines.append("\n=== SUBSYSTEMS ===")
            for subsystem in self.subsystems[:30]:
                lines.append(f"  - {subsystem}")
            if len(self.subsystems) > 30:
                lines.append(f"  ... and {len(self.subsystems) - 30} more")
        
        if self.signals:
            lines.append("\n=== SIGNAL CONNECTIONS (sample) ===")
            for signal in self.signals[:30]:
                src = signal.source_block or signal.source_port
                dst = signal.target_block or signal.target_port
                lines.append(f"  - {src} -> {dst}")
            if len(self.signals) > 30:
                lines.append(f"  ... and {len(self.signals) - 30} more signals")
        
        if self.configuration:
            lines.append("\n=== MODEL CONFIGURATION ===")
            for key, value in self.configuration.items():
                lines.append(f"  {key}: {value}")
        
        if self.parameters:
            lines.append("\n=== MODEL PARAMETERS ===")
            for key, value in self.parameters.items():
                if key != 'annotations':  # Skip annotations in main list
                    lines.append(f"  {key}: {value}")
        
        return "\n".join(lines)
    
    def get_block_by_name(self, name: str) -> Optional[SimulinkBlock]:
        """Get a block by its name."""
        for block in self.blocks:
            if block.name == name or block.path == name:
                return block
        return None
    
    def get_blocks_in_subsystem(self, subsystem_path: str) -> List[SimulinkBlock]:
        """Get all blocks within a specific subsystem."""
        return [b for b in self.blocks if b.parent == subsystem_path]

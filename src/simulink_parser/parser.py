"""
Simulink Model Parser

Parses .slx files to extract model structure, blocks, signals, and parameters.
Supports both MATLAB Engine API and XML parsing (no MATLAB required).
"""

import os
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional, Dict, Any, List
import json
import logging

from .models import SimulinkModel, SimulinkBlock, SimulinkSignal

logger = logging.getLogger(__name__)


class SimulinkParser:
    """
    Parser for Simulink (.slx) models.
    
    Supports two parsing methods:
    1. XML Parsing (no MATLAB required) - extracts basic structure
    2. MATLAB Engine API - extracts full model details (requires MATLAB)
    """
    
    def __init__(self, matlab_path: Optional[str] = None):
        """
        Initialize the parser.
        
        Args:
            matlab_path: Optional path to MATLAB installation
        """
        self.matlab_path = matlab_path
        self.matlab_engine = None
        self._matlab_available = False
        
        # Try to connect to MATLAB if path provided
        if matlab_path:
            self._init_matlab()
    
    def _init_matlab(self) -> bool:
        """Initialize MATLAB engine connection."""
        try:
            import matlab.engine
            self.matlab_engine = matlab.engine.start_matlab()
            self._matlab_available = True
            logger.info("MATLAB Engine connected successfully")
            return True
        except ImportError:
            logger.warning("MATLAB Engine for Python not available")
        except Exception as e:
            logger.warning(f"Could not connect to MATLAB: {e}")
        return False
    
    def parse(self, slx_file: str, use_matlab: bool = False) -> SimulinkModel:
        """
        Parse a Simulink model file.
        
        Args:
            slx_file: Path to the .slx file
            use_matlab: Force using MATLAB Engine (if available)
            
        Returns:
            SimulinkModel object with parsed data
        """
        if not os.path.exists(slx_file):
            raise FileNotFoundError(f"File not found: {slx_file}")
        
        # Get model name from filename
        model_name = Path(slx_file).stem
        
        # Use MATLAB if available and requested
        if use_matlab and self._matlab_available:
            return self._parse_with_matlab(slx_file, model_name)
        
        # Default to XML parsing
        return self._parse_with_xml(slx_file, model_name)
    
    def _parse_with_matlab(self, slx_file: str, model_name: str) -> SimulinkModel:
        """Parse using MATLAB Engine API (full details)."""
        logger.info(f"Parsing {slx_file} using MATLAB Engine")
        
        if not self._matlab_available:
            raise RuntimeError("MATLAB Engine not available")
        
        try:
            # Load the model
            self.matlab_engine.cd(os.path.dirname(slx_file))
            model = self.matlab_engine.load_system(model_name)
            
            blocks = []
            signals = []
            subsystems = []
            
            # Get all blocks
            all_blocks = self.matlab_engine.find_system(model, 'BlockType', '*')
            if all_blocks:
                if not isinstance(all_blocks, list):
                    all_blocks = [all_blocks]
                    
                for block_path in all_blocks:
                    try:
                        block = self._extract_block_from_matlab(model, block_path)
                        if block:
                            blocks.append(block)
                            if block.block_type == "SubSystem":
                                subsystems.append(block.path)
                    except Exception as e:
                        logger.debug(f"Could not extract block {block_path}: {e}")
            
            # Get configuration
            configuration = {}
            try:
                config_set = self.matlab_engine.getActiveConfigSet(model)
                configuration["solver"] = str(self.matlab_engine.get(config_set, 'Solver'))
                configuration["stopTime"] = str(self.matlab_engine.get(config_set, 'StopTime'))
            except:
                pass
            
            return SimulinkModel(
                name=model_name,
                file_path=slx_file,
                blocks=blocks,
                signals=signals,
                subsystems=subsystems,
                configuration=configuration
            )
            
        except Exception as e:
            logger.error(f"MATLAB parsing failed: {e}, falling back to XML")
            return self._parse_with_xml(slx_file, model_name)
    
    def _extract_block_from_matlab(self, model, block_path: str) -> Optional[SimulinkBlock]:
        """Extract block information using MATLAB API."""
        try:
            # Get block parameters
            params = {}
            try:
                handle = self.matlab_engine.get_param(block_path, 'Handle')
                # Common parameters to extract
                for param in ['BlockType', 'Name', 'Position', 'Parent', 'Ports']:
                    try:
                        value = self.matlab_engine.get_param(block_path, param)
                        if value:
                            params[param] = str(value)
                    except:
                        pass
            except:
                pass
            
            block_type = params.get('BlockType', 'Unknown')
            name = params.get('Name', block_path.split('/')[-1])
            position = params.get('Position', None)
            parent = params.get('Parent', None)
            
            # Parse position if available
            pos_list = None
            if position:
                try:
                    pos_str = position.strip('[]').split(';')
                    pos_list = [int(x.strip()) for x in pos_str]
                except:
                    pass
            
            # Parse ports
            ports = {}
            if 'Ports' in params:
                try:
                    ports_str = params['Ports'].strip('[]').split(',')
                    if len(ports_str) >= 1:
                        ports['inputs'] = [f"in{i+1}" for i in range(int(ports_str[0].strip()) or 0)]
                    if len(ports_str) >= 2:
                        ports['outputs'] = [f"out{i+1}" for i in range(int(ports_str[1].strip()) or 0)]
                except:
                    pass
            
            return SimulinkBlock(
                name=name,
                block_type=block_type,
                path=block_path,
                parameters=params,
                position=pos_list,
                parent=parent,
                ports=ports
            )
        except Exception as e:
            logger.debug(f"Error extracting block {block_path}: {e}")
            return None
    
    def _parse_with_xml(self, slx_file: str, model_name: str) -> SimulinkModel:
        """
        Parse .slx file as ZIP and extract XML structure.
        This method works without MATLAB installation.
        """
        logger.info(f"Parsing {slx_file} using XML extraction")
        
        blocks = []
        signals = []
        subsystems = []
        parameters = {}
        
        try:
            with zipfile.ZipFile(slx_file, 'r') as zf:
                # The main model XML is in simulink/simulink.r201ola (changes with version)
                # We need to find the correct archive
                model_xml = None
                
                for name in zf.namelist():
                    if 'simulink.xml' in name:
                        model_xml = zf.read(name)
                        break
                
                if model_xml:
                    root = ET.fromstring(model_xml)
                    
                    # Extract blocks
                    for block_elem in root.findall(".//{*}Block"):
                        block = self._parse_block_element(block_elem)
                        if block:
                            blocks.append(block)
                            if block.block_type == "SubSystem":
                                subsystems.append(block.path)
                    
                    # Extract lines (signals)
                    for line_elem in root.findall(".//{*}Line"):
                        signal = self._parse_line_element(line_elem)
                        if signal:
                            signals.append(signal)
                    
                    # Extract model parameters
                    for param_elem in root.findall(".//{*}Parameter"):
                        name_elem = param_elem.find("{*}Name")
                        value_elem = param_elem.find("{*}Value")
                        if name_elem is not None and value_elem is not None:
                            parameters[name_elem.text] = value_elem.text
                            
        except Exception as e:
            logger.error(f"XML parsing error: {e}")
            # Return empty model with error info
            return SimulinkModel(
                name=model_name,
                file_path=slx_file,
                blocks=[],
                signals=[],
                parameters={"error": str(e)}
            )
        
        return SimulinkModel(
            name=model_name,
            file_path=slx_file,
            blocks=blocks,
            signals=signals,
            subsystems=subsystems,
            parameters=parameters
        )
    
    def _parse_block_element(self, elem: ET.Element) -> Optional[SimulinkBlock]:
        """Parse a Block element from XML."""
        try:
            name = elem.get('Name', '')
            block_type = elem.get('BlockType', 'Unknown')
            path = elem.get('Path', '')
            
            # Get parameters
            parameters = {}
            for param in elem.findall(".//{*}Parameter"):
                param_name = param.get('Name', '')
                value_elem = param.find("{*}Value")
                if value_elem is not None and value_elem.text:
                    parameters[param_name] = value_elem.text
            
            # Get position
            position = None
            pos_elem = elem.find(".//{*}Position")
            if pos_elem is not None and pos_elem.text:
                try:
                    pos_parts = pos_elem.text.strip().split()
                    position = [int(p) for p in pos_parts]
                except:
                    pass
            
            # Get parent
            parent = None
            parent_elem = elem.find(".//{*}Parent")
            if parent_elem is not None and parent_elem.text:
                parent = parent_elem.text
            
            # Get ports
            ports = {}
            inports = elem.findall(".//{*}Port")
            if inports:
                ports['inputs'] = [f"in{i+1}" for i in range(len(inports))]
            
            return SimulinkBlock(
                name=name,
                block_type=block_type,
                path=path,
                parameters=parameters,
                position=position,
                parent=parent,
                ports=ports
            )
        except Exception as e:
            logger.debug(f"Error parsing block element: {e}")
            return None
    
    def _parse_line_element(self, elem: ET.Element) -> Optional[SimulinkSignal]:
        """Parse a Line element (signal connection) from XML."""
        try:
            # Get src and dst ports
            src = elem.find(".//{*}Src")
            dst = elem.find(".//{*}Dst")
            
            if src is None or dst is None:
                return None
            
            source_block = src.get('Block', '')
            source_port = src.get('Port', '')
            target_block = dst.get('Block', '')
            target_port = dst.get('Port', '')
            
            return SimulinkSignal(
                name=elem.get('Name', None),
                source_block=source_block,
                source_port=source_port,
                target_block=target_block,
                target_port=target_port
            )
        except Exception as e:
            logger.debug(f"Error parsing line element: {e}")
            return None
    
    def save_json(self, model: SimulinkModel, output_path: str) -> None:
        """Save parsed model to JSON file."""
        with open(output_path, 'w') as f:
            json.dump(model.to_dict(), f, indent=2)
        logger.info(f"Model saved to {output_path}")
    
    def analyze_model_structure(self, model: SimulinkModel) -> Dict[str, Any]:
        """
        Perform basic structural analysis on the model.
        
        Returns:
            Dictionary with analysis results
        """
        analysis = {
            "total_blocks": len(model.blocks),
            "total_signals": len(model.signals),
            "subsystem_count": len(model.subsystems),
            "block_types": {},
            "potential_issues": []
        }
        
        # Count block types
        for block in model.blocks:
            bt = block.block_type
            analysis["block_types"][bt] = analysis["block_types"].get(bt, 0) + 1
        
        # Check for potential issues
        # 1. Unconnected ports
        blocks_with_inputs = set()
        blocks_with_outputs = set()
        
        for signal in model.signals:
            blocks_with_inputs.add(signal.target_block)
            blocks_with_outputs.add(signal.source_block)
        
        for block in model.blocks:
            if block.path not in blocks_with_inputs and len(block.ports.get('inputs', [])) > 0:
                analysis["potential_issues"].append({
                    "type": "unconnected_input",
                    "block": block.path,
                    "severity": "warning"
                })
            
            if block.path not in blocks_with_outputs and len(block.ports.get('outputs', [])) > 0:
                analysis["potential_issues"].append({
                    "type": "unconnected_output", 
                    "block": block.path,
                    "severity": "warning"
                })
        
        # 2. Check for algebraic loops (simplified check)
        # This would need more sophisticated analysis
        
        return analysis

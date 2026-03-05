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
        
        Improved version with better XML namespace handling and extraction.
        """
        logger.info(f"Parsing {slx_file} using XML extraction")
        
        blocks = []
        signals = []
        subsystems = []
        parameters = {}
        
        try:
            with zipfile.ZipFile(slx_file, 'r') as zf:
                # List all files in the archive
                file_list = zf.namelist()
                logger.info(f"SLX archive contains {len(file_list)} files")
                
                # Find the main model XML - different Simulink versions use different paths
                model_xml = None
                found_xml_path = None
                xml_paths = [
                    'simulink/simulink.xml',
                    'simulink.xml',
                    'Simulink.xml',
                ]
                
                for xml_path in xml_paths:
                    if xml_path in file_list:
                        model_xml = zf.read(xml_path)
                        found_xml_path = xml_path
                        logger.info(f"Found model XML at: {xml_path}")
                        break
                
                # If not found, search for any XML file
                if not model_xml:
                    for name in file_list:
                        if name.endswith('.xml') and 'simulink' in name.lower():
                            model_xml = zf.read(name)
                            found_xml_path = name
                            logger.info(f"Found model XML at: {name}")
                            break
                
                # Also try to extract from block XML files
                block_xml_files = [f for f in file_list if 'simulink' in f.lower() and f.endswith('.xml')]
                
                if model_xml:
                    root = ET.fromstring(model_xml)
                    
                    # Try different XML namespaces used by Simulink
                    namespaces = [
                        {'': ''},  # No namespace
                        {'ns': 'http://www.mathworks.com/Schema/matlab/2016b/xml/matlab'},
                        {'ns': 'http://www.mathworks.com/Schema/matlab/2017a/xml/matlab'},
                        {'ns': 'http://www.mathworks.com/Schema/matlab/2019a/xml/matlab'},
                        {'ns': 'http://www.w3.org/2001/XMLSchema-instance'},
                    ]
                    
                    # Extract blocks - try multiple approaches
                    for ns in namespaces:
                        try:
                            blocks_elem = root.findall('.//Block', ns)
                            if not blocks_elem:
                                blocks_elem = root.findall('.//ns:Block', ns)
                            
                            if blocks_elem:
                                logger.info(f"Found {len(blocks_elem)} blocks with ns: {ns}")
                                for block_elem in blocks_elem:
                                    block = self._parse_block_element(block_elem, ns)
                                    if block:
                                        blocks.append(block)
                                        if block.block_type == "SubSystem":
                                            subsystems.append(block.path)
                                if blocks:
                                    break
                        except Exception as e:
                            logger.debug(f"Block extraction with ns {ns} failed: {e}")
                    
                    # If still no blocks, try without namespace
                    if not blocks:
                        logger.info("Trying fallback block extraction")
                        for elem in root.iter():
                            tag = elem.tag if isinstance(elem.tag, str) else ''
                            if 'Block' in tag:
                                block = self._parse_block_element(elem, {})
                                if block:
                                    blocks.append(block)
                                    if block.block_type == "SubSystem":
                                        subsystems.append(block.path)
                    
                    # Extract lines (signals) - try multiple approaches
                    for ns in namespaces:
                        try:
                            lines_elem = root.findall('.//Line', ns)
                            if not lines_elem:
                                lines_elem = root.findall('.//ns:Line', ns)
                            
                            if lines_elem:
                                logger.info(f"Found {len(lines_elem)} lines with ns: {ns}")
                                for line_elem in lines_elem:
                                    signal = self._parse_line_element(line_elem, ns)
                                    if signal:
                                        signals.append(signal)
                                if signals:
                                    break
                        except Exception as e:
                            logger.debug(f"Line extraction with ns {ns} failed: {e}")
                    
                    # If still no signals, try fallback
                    if not signals:
                        for elem in root.iter():
                            tag = elem.tag if isinstance(elem.tag, str) else ''
                            if 'Line' in tag:
                                signal = self._parse_line_element(elem, {})
                                if signal:
                                    signals.append(signal)
                    
                    # Extract model parameters
                    try:
                        config_elem = root.find('.//Configuration')
                        if config_elem is not None:
                            for param in config_elem:
                                param_name = param.get('Name', param.tag)
                                value_elem = param.find('Value')
                                if value_elem is not None and value_elem.text:
                                    parameters[param_name] = value_elem.text
                    except Exception as e:
                        logger.debug(f"Could not extract configuration: {e}")
                    
                    # Also look for annotations (descriptions)
                    annotations = []
                    for elem in root.iter():
                        tag = elem.tag if isinstance(elem.tag, str) else ''
                        if 'Annotation' in tag:
                            ann_text = elem.get('Name', '') or elem.get('Text', '')
                            if ann_text:
                                annotations.append(ann_text)
                    if annotations:
                        parameters['annotations'] = annotations
                else:
                    logger.warning(f"Could not find model XML in {slx_file}")
                    logger.info(f"Files in archive: {file_list[:20]}")
                    
        except Exception as e:
            logger.error(f"XML parsing error: {e}")
            import traceback
            traceback.print_exc()
            return SimulinkModel(
                name=model_name,
                file_path=slx_file,
                blocks=[],
                signals=[],
                parameters={"error": str(e)}
            )
        
        logger.info(f"Parsed: {len(blocks)} blocks, {len(signals)} signals")
        return SimulinkModel(
            name=model_name,
            file_path=slx_file,
            blocks=blocks,
            signals=signals,
            subsystems=subsystems,
            parameters=parameters
        )
    
    def _parse_block_element(self, elem: ET.Element, ns: Dict[str, str] = None) -> Optional[SimulinkBlock]:
        """Parse a Block element from XML with improved extraction."""
        try:
            ns = ns or {}
            
            # Get attributes - try different attribute names used by Simulink
            name = elem.get('Name', '') or elem.get('name', '')
            block_type = elem.get('BlockType', '') or elem.get('blockType', '') or elem.get('Type', '')
            path = elem.get('Path', '') or elem.get('path', '')
            
            # If we don't have name from attributes, try element text
            if not name:
                name = elem.text or ''
            
            # Get parameters from nested elements
            parameters = {}
            
            # Try different parameter paths
            for param_path in ['.//Parameter', './/ns:Parameter', './/p:Parameter', './/Property']:
                try:
                    params = elem.findall(param_path, ns)
                    for param in params:
                        param_name = param.get('Name', '') or param.get('name', '')
                        # Try different value paths
                        value_elem = param.find("{*}Value") or param.find("Value") or param.find("value")
                        if value_elem is not None and value_elem.text:
                            parameters[param_name] = value_elem.text
                except:
                    pass
            
            # Also extract direct child elements as parameters
            for child in elem:
                child_tag = child.tag if isinstance(child.tag, str) else ''
                # Clean namespace prefix
                if '}' in child_tag:
                    child_tag = child_tag.split('}')[1]
                
                # Only use meaningful attributes
                if child.text and child.text.strip():
                    if child_tag not in ['Block', 'Line', 'Port', 'Annotation']:
                        parameters[child_tag] = child.text.strip()
                
                # Also get attributes
                for attr_name, attr_value in child.attrib.items():
                    if attr_value:
                        parameters[f"{child_tag}_{attr_name}"] = attr_value
            
            # Get position
            position = None
            for pos_path in ['.//{*}Position', './/Position']:
                pos_elem = elem.find(pos_path)
                if pos_elem is not None:
                    pos_text = pos_elem.text if pos_elem.text else ''
                    if pos_text:
                        try:
                            pos_parts = pos_text.strip().split()
                            position = [int(p) for p in pos_parts]
                            break
                        except:
                            pass
            
            # Get parent
            parent = None
            for parent_path in ['.//{*}Parent', './/Parent']:
                parent_elem = elem.find(parent_path)
                if parent_elem is not None and parent_elem.text:
                    parent = parent_elem.text
                    break
            
            # Get ports - try different approaches
            ports = {}
            
            # From element attributes
            inports = elem.get('InPorts', '')
            outports = elem.get('OutPorts', '')
            
            if inports:
                try:
                    num_in = int(inports)
                    ports['inputs'] = [f"in{i+1}" for i in range(num_in)]
                except:
                    pass
            
            if outports:
                try:
                    num_out = int(outports)
                    ports['outputs'] = [f"out{i+1}" for i in range(num_out)]
                except:
                    pass
            
            # From nested elements
            if not ports:
                for port_elem in elem.findall('.//{*}Port') + elem.findall('.//Port'):
                    port_type = port_elem.get('Type', '') or port_elem.get('type', '')
                    port_index = port_elem.get('Index', '') or port_elem.get('index', '')
                    
                    if 'in' in str(port_type).lower() or 'input' in str(port_type).lower():
                        if 'inputs' not in ports:
                            ports['inputs'] = []
                        ports['inputs'].append(f"in{port_index or len(ports['inputs'])+1}")
                    elif 'out' in str(port_type).lower() or 'output' in str(port_type).lower():
                        if 'outputs' not in ports:
                            ports['outputs'] = []
                        ports['outputs'].append(f"out{port_index or len(ports['outputs'])+1}")
            
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
    
    def _parse_line_element(self, elem: ET.Element, ns: Dict[str, str] = None) -> Optional[SimulinkSignal]:
        """Parse a Line element (signal connection) from XML with improved extraction."""
        try:
            ns = ns or {}
            
            # Try to find source and destination elements - various Simulink formats
            source_block = ''
            source_port = ''
            target_block = ''
            target_port = ''
            
            # Method 1: Look for Src/Dst elements
            for src_path in ['.//{*}Src', './/Src', './/{*}Source', './/Source']:
                src = elem.find(src_path)
                if src is not None:
                    source_block = src.get('Block', '') or src.get('block', '') or src.text or ''
                    source_port = src.get('Port', '') or src.get('port', '') or ''
                    break
            
            for dst_path in ['.//{*}Dst', './/Dst', './/{*}Destination', './/Destination']:
                dst = elem.find(dst_path)
                if dst is not None:
                    target_block = dst.get('Block', '') or dst.get('block', '') or dst.text or ''
                    target_port = dst.get('Port', '') or dst.get('port', '') or ''
                    break
            
            # Method 2: If not found, look for Port elements
            if not source_block:
                for port in elem.findall('.//{*}Port') + elem.findall('.//Port'):
                    port_type = port.get('Type', '').lower()
                    if 'src' in port_type or 'out' in port_type:
                        source_block = port.get('Block', '') or port.text or ''
                        source_port = port.get('Index', '') or ''
                    elif 'dst' in port_type or 'in' in port_type:
                        target_block = port.get('Block', '') or port.text or ''
                        target_port = port.get('Index', '') or ''
            
            # Method 3: Get from element attributes directly
            if not source_block:
                source_block = elem.get('SrcBlock', '') or elem.get('srcBlock', '') or ''
                source_port = elem.get('SrcPort', '') or elem.get('srcPort', '') or ''
            
            if not target_block:
                target_block = elem.get('DstBlock', '') or elem.get('dstBlock', '') or ''
                target_port = elem.get('DstPort', '') or elem.get('dstPort', '') or ''
            
            # Get signal name
            signal_name = elem.get('Name', '') or elem.get('name', '')
            
            # Get signal properties (width, data type)
            signal_width = None
            data_type = None
            
            # Try to find signal properties
            for prop_path in ['.//{*}Prop', './/Prop', './/{*}Properties']:
                props = elem.findall(prop_path)
                for prop in props:
                    prop_name = prop.get('Name', '')
                    if 'width' in prop_name.lower():
                        try:
                            signal_width = int(prop.text or prop.get('Value', ''))
                        except:
                            pass
                    elif 'datatype' in prop_name.lower() or 'type' in prop_name.lower():
                        data_type = prop.text or prop.get('Value', '')
            
            # Only return if we have meaningful data
            if source_block or target_block:
                return SimulinkSignal(
                    name=signal_name or None,
                    source_block=source_block,
                    source_port=source_port,
                    target_block=target_block,
                    target_port=target_port,
                    signal_width=signal_width,
                    data_type=data_type
                )
            return None
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

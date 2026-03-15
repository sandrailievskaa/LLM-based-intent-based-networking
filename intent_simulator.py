"""
LLM-based Intent-Based Networking Simulator
============================================
A safe simulation of intent-based networking that translates natural language
intents into network flow rules without requiring Mininet or Ryu.

Architecture (SDN-style):
- Northbound: natural language intents (user input)
- Controller: intent parsing (LLM or regex) -> flow rules
- Southbound: flow rules applied to simulated data plane (switch)
"""

import json
import os
import re
import networkx as nx
import matplotlib.pyplot as plt
from typing import Dict, List, Tuple, Optional

# Optional: use real LLM if openai is installed and OPENAI_API_KEY is set
try:
    from openai import OpenAI
    _OPENAI_AVAILABLE = True
except ImportError:
    _OPENAI_AVAILABLE = False


class NetworkSimulator:
    """
    Simulates the DATA PLANE (Southbound): a simple topology with hosts and switch.
    Holds flow rules (like OpenFlow flow table) and enforces allow/block on ping.
    """
    
    def __init__(self):
        # Initialize network topology
        self.hosts = ['h1', 'h2', 'h3']
        self.switch = 's1'
        self.graph = nx.Graph()
        
        # Flow table (Southbound): match (src, dst) -> action (allow | block)
        self.flow_rules: List[Dict] = []
        
        # Build the network topology
        self._build_topology()
        
    def _build_topology(self):
        """Build the network graph with hosts connected to a central switch."""
        # Add nodes
        self.graph.add_node(self.switch, node_type='switch')
        for host in self.hosts:
            self.graph.add_node(host, node_type='host')
            # Connect each host to the switch
            self.graph.add_edge(host, self.switch)
    
    def add_flow_rule(self, action: str, src: str, dst: str) -> bool:
        """
        Add a flow rule to the network.
        
        Args:
            action: 'allow' or 'block'
            src: Source host (e.g., 'h1')
            dst: Destination host (e.g., 'h3')
        
        Returns:
            True if rule was added successfully, False otherwise
        """
        # Validate hosts
        if src not in self.hosts or dst not in self.hosts:
            print(f"Error: Invalid host(s). Valid hosts are: {self.hosts}")
            return False
        
        # Validate action
        action = action.lower()
        if action not in ['allow', 'block']:
            print(f"Error: Invalid action '{action}'. Use 'allow' or 'block'.")
            return False
        
        # Check for existing rule between these hosts
        for i, rule in enumerate(self.flow_rules):
            if rule['src'] == src and rule['dst'] == dst:
                # Update existing rule
                self.flow_rules[i] = {'action': action, 'src': src, 'dst': dst}
                print(f"Updated existing rule: {action.upper()} {src} -> {dst}")
                return True
        
        # Add new rule
        new_rule = {'action': action, 'src': src, 'dst': dst}
        self.flow_rules.append(new_rule)
        print(f"Added flow rule: {action.upper()} {src} -> {dst}")
        return True
    
    def remove_flow_rule(self, src: str, dst: str) -> bool:
        """Remove a flow rule between src and dst."""
        for i, rule in enumerate(self.flow_rules):
            if rule['src'] == src and rule['dst'] == dst:
                removed = self.flow_rules.pop(i)
                print(f"Removed flow rule: {removed['action'].upper()} {src} -> {dst}")
                return True
        print(f"No rule found for {src} -> {dst}")
        return False
    
    def get_flow_rules(self) -> List[Dict]:
        """Return all current flow rules."""
        return self.flow_rules.copy()
    
    def clear_flow_rules(self):
        """Clear all flow rules."""
        self.flow_rules.clear()
        print("All flow rules cleared.")
    
    def _check_connectivity(self, src: str, dst: str) -> Tuple[bool, Optional[Dict]]:
        """
        Check if traffic from src to dst is allowed based on flow rules.
        
        Returns:
            Tuple of (is_allowed, blocking_rule or None)
        """
        # Check for specific rules
        for rule in self.flow_rules:
            if rule['src'] == src and rule['dst'] == dst:
                if rule['action'] == 'block':
                    return (False, rule)
                else:
                    return (True, None)
        
        # Default: allow if no blocking rule exists
        return (True, None)
    
    def ping(self, src: str, dst: str) -> str:
        """
        Simulate a ping from src to dst.
        
        Args:
            src: Source host
            dst: Destination host
        
        Returns:
            Result string indicating SUCCESS or BLOCKED
        """
        if src not in self.hosts:
            return f"Error: Unknown host '{src}'"
        if dst not in self.hosts:
            return f"Error: Unknown host '{dst}'"
        if src == dst:
            return f"Ping {src} -> {dst}: SUCCESS (localhost)"
        
        is_allowed, blocking_rule = self._check_connectivity(src, dst)
        
        if is_allowed:
            return f"Ping {src} -> {dst}: SUCCESS"
        else:
            rule_json = json.dumps(blocking_rule)
            return f"Ping {src} -> {dst}: BLOCKED by flow rule {rule_json}"
    
    def ping_all(self) -> List[str]:
        """Simulate ping between all host pairs."""
        results = []
        for src in self.hosts:
            for dst in self.hosts:
                if src != dst:
                    results.append(self.ping(src, dst))
        return results
    
    def display_topology(self, show_rules: bool = True):
        """
        Display the network topology using matplotlib.
        
        Args:
            show_rules: If True, display flow rules on the plot
        """
        plt.figure(figsize=(10, 8))
        
        # Create position layout
        pos = {
            's1': (0.5, 0.5),
            'h1': (0.2, 0.8),
            'h2': (0.8, 0.8),
            'h3': (0.5, 0.2)
        }
        
        # Draw nodes with different colors for hosts and switch
        host_nodes = [n for n in self.graph.nodes() if self.graph.nodes[n].get('node_type') == 'host']
        switch_nodes = [n for n in self.graph.nodes() if self.graph.nodes[n].get('node_type') == 'switch']
        
        # Draw switch
        nx.draw_networkx_nodes(self.graph, pos, nodelist=switch_nodes, 
                               node_color='lightblue', node_size=2000, 
                               node_shape='s', label='Switch')
        
        # Draw hosts
        nx.draw_networkx_nodes(self.graph, pos, nodelist=host_nodes,
                               node_color='lightgreen', node_size=1500,
                               node_shape='o', label='Hosts')
        
        # Draw edges
        nx.draw_networkx_edges(self.graph, pos, edge_color='gray', width=2)
        
        # Draw labels
        nx.draw_networkx_labels(self.graph, pos, font_size=12, font_weight='bold')
        
        # Add title and flow rules info
        plt.title("Network Topology\n(3 Hosts + 1 Switch)", fontsize=14, fontweight='bold')
        
        if show_rules and self.flow_rules:
            rules_text = "Active Flow Rules:\n"
            for rule in self.flow_rules:
                rules_text += f"  {rule['action'].upper()}: {rule['src']} -> {rule['dst']}\n"
            plt.text(0.02, 0.02, rules_text, transform=plt.gca().transAxes, 
                    fontsize=10, verticalalignment='bottom',
                    bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        plt.axis('off')
        plt.tight_layout()
        plt.legend(loc='upper right')
        plt.show()


class IntentParser:
    """
    Northbound -> Controller: parses natural language intents into flow rules.
    Uses pattern matching (regex) by default; can use real LLM if configured.
    """
    
    # Intent patterns for parsing natural language
    INTENT_PATTERNS = [
        # Block patterns
        (r'block\s+(\w+)\s+(?:from\s+)?(?:accessing|to|reaching|connecting\s+to)\s+(\w+)', 'block'),
        (r'deny\s+(\w+)\s+(?:access\s+to|to)\s+(\w+)', 'block'),
        (r'prevent\s+(\w+)\s+(?:from\s+)?(?:accessing|reaching|connecting\s+to)\s+(\w+)', 'block'),
        (r'drop\s+(?:traffic\s+)?(?:from\s+)?(\w+)\s+to\s+(\w+)', 'block'),
        (r'disable\s+(?:connection\s+)?(?:from\s+)?(\w+)\s+to\s+(\w+)', 'block'),
        (r'isolate\s+(\w+)\s+from\s+(\w+)', 'block'),
        
        # Allow patterns
        (r'allow\s+(\w+)\s+(?:to\s+)?(?:access|reach|connect\s+to)?\s*(\w+)', 'allow'),
        (r'permit\s+(\w+)\s+(?:to\s+)?(?:access)?\s*(\w+)', 'allow'),
        (r'enable\s+(?:connection\s+)?(?:from\s+)?(\w+)\s+to\s+(\w+)', 'allow'),
        (r'unblock\s+(\w+)\s+(?:to|from)\s+(\w+)', 'allow'),
        (r'let\s+(\w+)\s+(?:access|reach|connect\s+to)\s+(\w+)', 'allow'),
    ]
    
    def __init__(self, valid_hosts: List[str]):
        self.valid_hosts = [h.lower() for h in valid_hosts]

    def _parse_llm_response(self, text: str) -> Optional[Dict]:
        """Extract action, src, dst from LLM response (JSON or markdown code block)."""
        text = text.strip()
        # Extract JSON from ```json ... ``` if present
        if "```" in text:
            start = text.find("```json")
            if start == -1:
                start = text.find("```")
            if start != -1:
                start = text.find("\n", start) + 1 if "\n" in text[start:] else start + 3
                end = text.find("```", start)
                if end != -1:
                    text = text[start:end]
        # Find first { ... } and parse
        i = text.find("{")
        if i == -1:
            return None
        depth = 0
        for j in range(i, len(text)):
            if text[j] == "{":
                depth += 1
            elif text[j] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        obj = json.loads(text[i : j + 1])
                        action = (obj.get("action") or "").lower()
                        src = (obj.get("src") or "").lower()
                        dst = (obj.get("dst") or "").lower()
                        if action in ("allow", "block") and src in self.valid_hosts and dst in self.valid_hosts:
                            return {"action": action, "src": src, "dst": dst}
                    except (json.JSONDecodeError, TypeError):
                        pass
                    return None
        return None

    def parse_intent_with_llm(self, intent: str) -> Optional[Dict]:
        """
        Parse intent using OpenAI API if available and OPENAI_API_KEY is set.
        Returns None on failure or if LLM not available (then use parse_intent).
        """
        if not _OPENAI_AVAILABLE:
            return None
        api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        if not api_key:
            return None
        try:
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a network intent parser. Given a natural language network intent, "
                            "respond with ONLY a JSON object: {\"action\": \"allow\" or \"block\", \"src\": \"h1\" or \"h2\" or \"h3\", \"dst\": \"h1\" or \"h2\" or \"h3\"}. "
                            "Valid hosts are h1, h2, h3. No other text."
                        ),
                    },
                    {"role": "user", "content": intent},
                ],
                temperature=0,
            )
            text = (response.choices[0].message.content or "").strip()
            return self._parse_llm_response(text)
        except Exception:
            return None

    def parse_intent(self, intent: str) -> Optional[Dict]:
        """
        Parse a natural language intent into a flow rule.
        
        Args:
            intent: Natural language intent string
        
        Returns:
            Dict with 'action', 'src', 'dst' or None if parsing fails
        """
        intent_lower = intent.lower().strip()
        
        for pattern, action in self.INTENT_PATTERNS:
            match = re.search(pattern, intent_lower)
            if match:
                src = match.group(1).lower()
                dst = match.group(2).lower()
                
                # Validate hosts
                if src in self.valid_hosts and dst in self.valid_hosts:
                    return {
                        'action': action,
                        'src': src,
                        'dst': dst
                    }
                else:
                    invalid = []
                    if src not in self.valid_hosts:
                        invalid.append(src)
                    if dst not in self.valid_hosts:
                        invalid.append(dst)
                    print(f"Warning: Invalid host(s) in intent: {invalid}")
                    print(f"Valid hosts are: {self.valid_hosts}")
                    return None
        
        # No pattern matched
        return None
    
    def translate_intent_to_json(self, intent: str) -> str:
        """
        Translate an intent to a JSON flow rule string.
        
        Args:
            intent: Natural language intent
        
        Returns:
            JSON string of the flow rule or error message
        """
        rule = self.parse_intent(intent)
        if rule:
            return json.dumps(rule, indent=2)
        else:
            return json.dumps({
                "error": "Could not parse intent",
                "intent": intent,
                "hint": "Try formats like 'Block h1 from accessing h3' or 'Allow h2 to h3'"
            }, indent=2)


class IntentBasedNetworkController:
    """
    SDN Controller: Northbound (intents) -> parsing -> Southbound (flow rules).
    Combines IntentParser and NetworkSimulator for intent-based management.
    """
    
    def __init__(self, use_llm: bool = False):
        self.network = NetworkSimulator()
        self.parser = IntentParser(self.network.hosts)
        self.intent_history: List[str] = []
        self.use_llm = use_llm and _OPENAI_AVAILABLE and bool(os.environ.get("OPENAI_API_KEY", "").strip())
    
    def process_intent(self, intent: str) -> Dict:
        """
        Process a natural language intent and apply it to the network.
        
        Args:
            intent: Natural language network intent
        
        Returns:
            Dict with processing results
        """
        print(f"\n{'='*60}")
        print(f"Processing Intent: \"{intent}\"")
        print('='*60)
        
        # Northbound: parse intent (LLM or regex)
        rule = None
        if self.use_llm:
            rule = self.parser.parse_intent_with_llm(intent)
            if rule:
                print("(Parsed with LLM)")
        if rule is None:
            rule = self.parser.parse_intent(intent)
            if rule:
                print("(Parsed with pattern matching)")
        
        if rule is None:
            result = {
                'success': False,
                'intent': intent,
                'error': 'Could not parse intent',
                'suggestion': "Try formats like 'Block h1 from accessing h3' or 'Allow h2 to h3'"
            }
            print(f"ERROR: {result['error']}")
            print(f"Suggestion: {result['suggestion']}")
            return result
        
        # Show the translated JSON rule
        print(f"\nTranslated to JSON flow rule:")
        print(json.dumps(rule, indent=2))
        
        # Southbound: apply flow rule to data plane
        success = self.network.add_flow_rule(rule['action'], rule['src'], rule['dst'])
        
        if success:
            self.intent_history.append(intent)
        
        result = {
            'success': success,
            'intent': intent,
            'flow_rule': rule,
            'current_rules': self.network.get_flow_rules()
        }
        
        return result
    
    def test_connectivity(self):
        """Test and display connectivity between all hosts."""
        print(f"\n{'='*60}")
        print("Testing Network Connectivity (Ping All)")
        print('='*60)
        
        results = self.network.ping_all()
        for result in results:
            # Color coding for terminal (if supported)
            if 'SUCCESS' in result:
                print(f"  ✓ {result}")
            else:
                print(f"  ✗ {result}")
        
        return results
    
    def show_topology(self):
        """Display the network topology."""
        self.network.display_topology()
    
    def show_status(self):
        """Display current network status and flow table (Southbound)."""
        print(f"\n{'='*60}")
        print("Network Status")
        print('='*60)
        print(f"Hosts: {self.network.hosts}")
        print(f"Switch: {self.network.switch}")
        print(f"\nFlow Table (Southbound) — match (src -> dst) -> action:")
        if self.network.flow_rules:
            for i, rule in enumerate(self.network.flow_rules, 1):
                action = "DROP" if rule["action"] == "block" else "FORWARD"
                print(f"  {i}. match: {rule['src']} -> {rule['dst']}  |  action: {action}")
        else:
            print("  (No flow rules — default: allow all)")
        print(f"\nIntent History (Northbound) ({len(self.intent_history)}):")
        if self.intent_history:
            for i, intent in enumerate(self.intent_history, 1):
                print(f"  {i}. \"{intent}\"")
        else:
            print("  (No intents processed)")
    
    def interactive_mode(self):
        """Run the controller in interactive mode."""
        print("\n" + "="*60)
        print("LLM-based Intent-Based Networking Simulator")
        print("="*60)
        print("\nThis simulator demonstrates how natural language intents")
        print("can be translated into network flow rules (Northbound -> Southbound).")
        print(f"\nNetwork: {self.network.hosts} connected via {self.network.switch}")
        if self.use_llm:
            print("Mode: LLM parsing (OPENAI_API_KEY set)")
        else:
            print("Mode: Pattern matching (use --llm and set OPENAI_API_KEY for LLM)")
        print("\nCommands:")
        print("  - Type a network intent (e.g., 'Block h1 from accessing h3')")
        print("  - 'ping' - Test connectivity between all hosts")
        print("  - 'ping <src> <dst>' - Test specific connection")
        print("  - 'show' - Display network topology")
        print("  - 'status' - Show current flow rules")
        print("  - 'clear' - Clear all flow rules")
        print("  - 'help' - Show example intents")
        print("  - 'quit' or 'exit' - Exit the simulator")
        print("-"*60)
        
        while True:
            try:
                user_input = input("\nEnter intent or command: ").strip()
                
                if not user_input:
                    continue
                
                cmd = user_input.lower()
                
                if cmd in ['quit', 'exit', 'q']:
                    print("Exiting simulator. Goodbye!")
                    break
                
                elif cmd == 'ping':
                    self.test_connectivity()
                
                elif cmd.startswith('ping '):
                    parts = cmd.split()
                    if len(parts) == 3:
                        result = self.network.ping(parts[1], parts[2])
                        print(f"  {result}")
                    else:
                        print("Usage: ping <src> <dst> (e.g., 'ping h1 h3')")
                
                elif cmd == 'show':
                    self.show_topology()
                
                elif cmd == 'status':
                    self.show_status()
                
                elif cmd == 'clear':
                    self.network.clear_flow_rules()
                    self.intent_history.clear()
                
                elif cmd == 'help':
                    print("\nExample intents to try:")
                    print("  - 'Block h1 from accessing h3'")
                    print("  - 'Allow h2 to h3'")
                    print("  - 'Allow h1 to h2'")
                    print("  - 'Deny h1 access to h2'")
                    print("  - 'Permit h3 to access h1'")
                    print("  - 'Prevent h2 from reaching h1'")
                    print("  - 'Enable connection from h1 to h3'")
                    print("  - 'Isolate h2 from h3'")
                
                else:
                    # Treat as an intent
                    self.process_intent(user_input)
                    
            except KeyboardInterrupt:
                print("\n\nInterrupted. Exiting...")
                break
            except Exception as e:
                print(f"Error: {e}")


def demo_mode(use_llm: bool = False):
    """Run a demonstration of the simulator with example intents."""
    print("\n" + "="*60)
    print("LLM-based Intent-Based Networking - DEMO MODE")
    print("="*60)
    
    controller = IntentBasedNetworkController(use_llm=use_llm)
    
    # Show initial status
    controller.show_status()
    
    # Test initial connectivity (all should succeed)
    print("\n--- Initial Connectivity Test ---")
    controller.test_connectivity()
    
    # Process example intents
    example_intents = [
        "Block h1 from accessing h3",
        "Allow h2 to h3",
        "Allow h1 to h2",
    ]
    
    print("\n--- Processing Example Intents ---")
    for intent in example_intents:
        controller.process_intent(intent)
    
    # Show updated status
    controller.show_status()
    
    # Test connectivity after rules applied
    print("\n--- Connectivity Test After Rules Applied ---")
    controller.test_connectivity()
    
    # Display topology
    print("\n--- Displaying Network Topology ---")
    print("(A matplotlib window will open showing the network topology)")
    controller.show_topology()
    
    return controller


def main():
    """Main entry point for the simulator."""
    import sys
    use_llm = "--llm" in sys.argv
    if "--demo" in sys.argv:
        demo_mode(use_llm=use_llm)
    else:
        controller = IntentBasedNetworkController(use_llm=use_llm)
        controller.interactive_mode()


if __name__ == "__main__":
    main()

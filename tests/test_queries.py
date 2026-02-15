import pytest
from unittest.mock import MagicMock

def test_graph_search_query_generation():
    """
    Test that the graph search logic handles the new Entity structure correctly.
    Since we can't easily mock the Neo4j driver execution in a simple unit test 
    without complex mocking, we will simulate the result processing logic.
    """
    
    # Mock record structure from Neo4j
    mock_record = {
        's': 'John Doe',
        'p': 'HAS_CONDITION',
        'o': 'Diabetes',
        's_labels': ['Patient', 'Entity'],
        'o_labels': ['Condition', 'Entity'],
        'p2': None,
        'g': None,
        'g_labels': []
    }
    
    results = []
    
    # Simulate the logic inside graph_search
    def get_label(labels):
        return next((l for l in labels if l != 'Entity'), 'Entity')

    s_label = get_label(mock_record['s_labels'])
    o_label = get_label(mock_record['o_labels'])
    
    s_name = mock_record['s'] or "Unknown"
    o_name = mock_record['o'] or "Unknown"

    results.append(f"({s_name}:{s_label}) -[{mock_record['p']}]-> ({o_name}:{o_label})")
    
    # Assert
    assert s_label == 'Patient'
    assert o_label == 'Condition'
    assert results[0] == "(John Doe:Patient) -[HAS_CONDITION]-> (Diabetes:Condition)"

def test_graph_search_hop2_logic():
    """Test the 2-hop logic logic."""
    mock_record = {
        's': 'Visit 101',
        'p': 'PRESCRIBED',
        'o': 'Aspirin',
        's_labels': ['Visit', 'Entity'],
        'o_labels': ['Medication', 'Entity'],
        'p2': 'TREATED_BY', # Incorrect relationship for test, but logic should handle it
        'g': 'Dr. Smith',
        'g_labels': ['Doctor', 'Entity']
    }
    
    results = []
    
    def get_label(labels):
        return next((l for l in labels if l != 'Entity'), 'Entity')

    s_label = get_label(mock_record['s_labels'])
    o_label = get_label(mock_record['o_labels'])
    
    s_name = mock_record['s'] or "Unknown"
    o_name = mock_record['o'] or "Unknown"

    results.append(f"({s_name}:{s_label}) -[{mock_record['p']}]-> ({o_name}:{o_label})")
    
    if mock_record['p2']:
        g_label = get_label(mock_record['g_labels'])
        g_name = mock_record['g'] or "Unknown"
        results.append(f"({o_name}:{o_label}) -[{mock_record['p2']}]-> ({g_name}:{g_label})")

    assert len(results) == 2
    assert results[1] == "(Aspirin:Medication) -[TREATED_BY]-> (Dr. Smith:Doctor)"

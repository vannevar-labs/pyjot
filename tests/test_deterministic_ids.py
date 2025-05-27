from jot.util import generate_trace_id, generate_span_id, set_test_random_seed, clear_test_random_seed, format_trace_id, format_span_id


def test_deterministic_id_generation():
    """Test that setting a seed produces deterministic ID generation."""
    # Set a seed and generate IDs
    set_test_random_seed(42)
    trace_id_1 = generate_trace_id()
    span_id_1 = generate_span_id()
    
    # Reset to the same seed and generate again
    set_test_random_seed(42)
    trace_id_2 = generate_trace_id()
    span_id_2 = generate_span_id()
    
    # Should be identical
    assert trace_id_1 == trace_id_2
    assert span_id_1 == span_id_2
    
    # Clean up
    clear_test_random_seed()


def test_different_seeds_produce_different_ids():
    """Test that different seeds produce different IDs."""
    # Generate with seed 1
    set_test_random_seed(1)
    trace_id_1 = generate_trace_id()
    span_id_1 = generate_span_id()
    
    # Generate with seed 2
    set_test_random_seed(2)
    trace_id_2 = generate_trace_id()
    span_id_2 = generate_span_id()
    
    # Should be different
    assert trace_id_1 != trace_id_2
    assert span_id_1 != span_id_2
    
    # Clean up
    clear_test_random_seed()


def test_random_behavior_after_clearing_seed():
    """Test that random behavior is restored after clearing the seed."""
    # Set deterministic behavior
    set_test_random_seed(123)
    deterministic_trace = generate_trace_id()
    
    # Clear seed and generate multiple IDs
    clear_test_random_seed()
    random_trace_1 = generate_trace_id()
    random_trace_2 = generate_trace_id()
    
    # Random IDs should be different from each other and from deterministic one
    assert random_trace_1 != random_trace_2
    assert random_trace_1 != deterministic_trace
    assert random_trace_2 != deterministic_trace


def test_formatted_id_consistency():
    """Test that formatted IDs are consistent with deterministic generation."""
    set_test_random_seed(999)
    trace_id = generate_trace_id()
    span_id = generate_span_id()
    
    # Format the IDs
    formatted_trace = format_trace_id(trace_id)
    formatted_span = format_span_id(span_id)
    
    # Check expected lengths
    assert len(formatted_trace) == 32  # 128 bits = 32 hex chars
    assert len(formatted_span) == 16   # 64 bits = 16 hex chars
    
    # Verify they're valid hex strings
    assert all(c in '0123456789abcdef' for c in formatted_trace)
    assert all(c in '0123456789abcdef' for c in formatted_span)
    
    # Reset seed and verify same formatting
    set_test_random_seed(999)
    trace_id_2 = generate_trace_id()
    span_id_2 = generate_span_id()
    
    assert format_trace_id(trace_id_2) == formatted_trace
    assert format_span_id(span_id_2) == formatted_span
    
    # Clean up
    clear_test_random_seed()
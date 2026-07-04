import os
import sys
import numpy as np
import openvino as ov
import onnxruntime as ort
import onnx
from onnx import helper, TensorProto

def main():
    onnx_path = "simple_add.onnx"
    print("=== Step 1: Creating a simple ONNX Model using ONNX Helper ===")
    
    # We will build a simple element-wise addition model: Z = X + Y
    # Inputs: X (1x4), Y (1x4)
    # Output: Z (1x4)
    
    # Define inputs and outputs
    X = helper.make_tensor_value_info('X', TensorProto.FLOAT, [1, 4])
    Y = helper.make_tensor_value_info('Y', TensorProto.FLOAT, [1, 4])
    Z = helper.make_tensor_value_info('Z', TensorProto.FLOAT, [1, 4])

    # Create the Add node
    node_def = helper.make_node(
        'Add',
        inputs=['X', 'Y'],
        outputs=['Z'],
        name='add_node'
    )

    # Create the graph definition
    graph_def = helper.make_graph(
        nodes=[node_def],
        name='SimpleAddGraph',
        inputs=[X, Y],
        outputs=[Z]
    )

    # Create and save the model
    onnx_model = helper.make_model(graph_def, producer_name='onnx-openvino-demo')
    onnx.save(onnx_model, onnx_path)
    print(f"ONNX model created and saved to: {os.path.abspath(onnx_path)}")

    # Input data
    x_data = np.array([[1.0, 2.0, 3.0, 4.0]], dtype=np.float32)
    y_data = np.array([[10.0, 20.0, 30.0, 40.0]], dtype=np.float32)
    expected_output = x_data + y_data
    print(f"Input X: {x_data}")
    print(f"Input Y: {y_data}")
    print(f"Expected Math Output (X + Y): {expected_output}")

    print("\n=== Step 2: Native OpenVINO Inference (Direct ONNX Load) ===")
    # Initialize OpenVINO Core
    core = ov.Core()
    
    # Read ONNX file directly (OpenVINO ONNX Frontend parses it at runtime)
    ov_model = core.read_model(onnx_path)
    
    # Compile the model for the target device (CPU)
    compiled_model = core.compile_model(ov_model, "CPU")
    
    # Perform inference passing inputs by name
    ov_results = compiled_model({"X": x_data, "Y": y_data})
    
    # Retrieve output using node name or output port index
    ov_output = ov_results["Z"]
    print(f"OpenVINO Output: {ov_output}")

    print("\n=== Step 3: ONNX Runtime Inference ===")
    # Determine execution provider
    available_providers = ort.get_available_providers()
    print(f"Available Providers: {available_providers}")
    
    selected_provider = "OpenVINOExecutionProvider"
    if selected_provider not in available_providers:
        print(f"Warning: '{selected_provider}' not available in this onnxruntime package.")
        print("Falling back to 'CPUExecutionProvider'.")
        selected_provider = "CPUExecutionProvider"
        
    # Start session with selected provider
    session = ort.InferenceSession(onnx_path, providers=[selected_provider])
    
    # Run session
    ort_results = session.run(["Z"], {"X": x_data, "Y": y_data})
    ort_output = ort_results[0]
    print(f"ONNX Runtime Output (using {selected_provider}): {ort_output}")

    # Validate matching outputs
    assert np.allclose(expected_output, ov_output, atol=1e-5), "OpenVINO output mismatch!"
    assert np.allclose(expected_output, ort_output, atol=1e-5), "ONNX Runtime output mismatch!"
    print("\n[SUCCESS] Verification: All outputs match perfectly!")

    # Clean up the generated ONNX file
    try:
        os.remove(onnx_path)
        print(f"Cleaned up temporary ONNX file: {onnx_path}")
    except OSError:
        pass

if __name__ == "__main__":
    main()

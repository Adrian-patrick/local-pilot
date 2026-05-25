import sys
import asyncio
from agentic_system.graph import local_pilot_graph, UserActionNode
from agentic_system.models import SharedState

async def run_pipeline():
    print("="*80)
    print("                 LOCAL PILOT AGENTIC ARCHITECTURE SIMULATOR")
    print("="*80)
    
    # 1. Resolve targets from CLI arguments (Default to README.md if none provided)
    if len(sys.argv) > 1:
        target_file = sys.argv[1]
        print(f"Target selected via CLI argument: '{target_file}'")
    else:
        target_file = "README.md"
        print(f"No target specified. Using default workspace context: '{target_file}'")

    # 2. Instantiate shared memory state
    state = SharedState()

    # 3. Create entrypoint node and run the state machine graph
    entrypoint_node = UserActionNode(target_file)
    
    print("\nStarting Pydantic Graph agent pipeline execution...")
    try:
        # Run graph to completion
        result = await local_pilot_graph.run(entrypoint_node, state=state)
        print(f"\nFinal Pipeline Status: {result.output.status.upper()}")
        print(f"Final Pipeline Message: {result.output.message}")
    except Exception as e:
        print(f"\n[FATAL ERROR] Pipeline crashed during graph execution: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
        
    print("\n" + "="*80)
    print("                 SIMULATION COMPLETED SUCCESSFULLY")
    print("="*80)

if __name__ == "__main__":
    # Handle event loop execution
    asyncio.run(run_pipeline())

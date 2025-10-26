#!/usr/bin/env python3
"""
Quick test runner to check ./run test functionality
"""
import subprocess
import sys
import os

def main():
    # Change to project directory
    project_dir = "/Users/blas/Documents/Obsidian Vault/School/F25/ECE 461/Project Repo/ECE30861_HW1"
    os.chdir(project_dir)
    
    print("Running ./run test...")
    print("=" * 50)
    
    try:
        # Run the test command
        result = subprocess.run(['./run', 'test'], 
                              capture_output=True, 
                              text=True, 
                              timeout=120)
        
        print("STDOUT:")
        print(result.stdout)
        
        if result.stderr:
            print("\nSTDERR:")
            print(result.stderr)
        
        print(f"\nReturn code: {result.returncode}")
        
        if result.returncode == 0:
            print("✅ Tests completed successfully!")
        else:
            print("❌ Tests failed or had errors")
            
    except subprocess.TimeoutExpired:
        print("❌ Test command timed out (>120s)")
    except FileNotFoundError:
        print("❌ ./run file not found or not executable")
    except Exception as e:
        print(f"❌ Error running tests: {e}")

if __name__ == "__main__":
    main()

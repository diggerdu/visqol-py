"""Command-line interface for ViSQOL-Py."""

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from .visqol import ViSQOL, ViSQOLMode
from .utils import load_batch_csv, save_results


def main():
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    try:
        if args.batch_input_csv:
            run_batch_mode(args)
        else:
            run_single_mode(args)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def create_parser() -> argparse.ArgumentParser:
    """Create command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="ViSQOL-Py: Python wrapper for ViSQOL audio quality metrics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Compare two audio files
  visqol-py --reference ref.wav --degraded deg.wav --verbose
  
  # Batch processing with CSV
  visqol-py --batch_input_csv input.csv --results_csv output.csv
  
  # Speech mode
  visqol-py --reference ref.wav --degraded deg.wav --use_speech_mode --verbose
        """
    )
    
    # Input files
    parser.add_argument(
        '--reference_file',
        type=str,
        help='Reference audio file path'
    )
    
    parser.add_argument(
        '--degraded_file', 
        type=str,
        help='Degraded audio file path'
    )
    
    parser.add_argument(
        '--batch_input_csv',
        type=str,
        help='CSV file with reference,degraded file pairs'
    )
    
    # Output options
    parser.add_argument(
        '--results_csv',
        type=str,
        help='Output CSV file for results'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Print detailed results to console'
    )
    
    parser.add_argument(
        '--output_debug',
        type=str,
        help='Output debug information to JSON file'
    )
    
    # ViSQOL options
    parser.add_argument(
        '--use_speech_mode',
        action='store_true',
        help='Use speech mode (16kHz) instead of audio mode (48kHz)'
    )
    
    return parser


def run_single_mode(args):
    """Run ViSQOL on a single file pair."""
    if not args.reference_file or not args.degraded_file:
        raise ValueError("Both --reference_file and --degraded_file are required for single mode")
    
    # Check if files exist
    ref_path = Path(args.reference_file)
    deg_path = Path(args.degraded_file)
    
    if not ref_path.exists():
        raise FileNotFoundError(f"Reference file not found: {ref_path}")
    if not deg_path.exists():
        raise FileNotFoundError(f"Degraded file not found: {deg_path}")
    
    # Initialize ViSQOL
    mode = ViSQOLMode.SPEECH if args.use_speech_mode else ViSQOLMode.AUDIO
    visqol = ViSQOL(mode=mode)
    
    # Compute score
    result = visqol.measure(ref_path, deg_path)
    
    # Output results
    if args.verbose:
        print(f"Reference: {args.reference_file}")
        print(f"Degraded: {args.degraded_file}")
        print(f"MOS-LQO: {result.moslqo:.6f}")
        if result.vnsim > 0:
            print(f"VNSIM: {result.vnsim:.6f}")
    else:
        print(f"{result.moslqo:.6f}")
    
    # Save to CSV if requested
    if args.results_csv:
        save_results([result], args.results_csv, format='csv')
        if args.verbose:
            print(f"Results saved to: {args.results_csv}")


def run_batch_mode(args):
    """Run ViSQOL on multiple file pairs from CSV."""
    if not args.batch_input_csv:
        raise ValueError("--batch_input_csv is required for batch mode")
    
    # Load file pairs
    csv_path = Path(args.batch_input_csv)
    if not csv_path.exists():
        raise FileNotFoundError(f"Batch CSV file not found: {csv_path}")
    
    file_pairs = load_batch_csv(csv_path)
    if not file_pairs:
        raise ValueError("No valid file pairs found in CSV")
    
    # Initialize ViSQOL
    mode = ViSQOLMode.SPEECH if args.use_speech_mode else ViSQOLMode.AUDIO
    visqol = ViSQOL(mode=mode)
    
    # Process all pairs
    print(f"Processing {len(file_pairs)} file pairs...")
    results = visqol.measure_batch(file_pairs)
    
    # Output results
    if args.verbose:
        print("\nResults:")
        print("-" * 80)
        for result in results:
            print(f"{result.reference_path} -> {result.degraded_path}: {result.moslqo:.6f}")
    
    # Save results
    if args.results_csv:
        save_results(results, args.results_csv, format='csv')
        print(f"Results saved to: {args.results_csv}")
    else:
        # Print summary
        scores = [r.moslqo for r in results]
        print(f"Mean MOS-LQO: {sum(scores)/len(scores):.6f}")
        print(f"Min MOS-LQO: {min(scores):.6f}")
        print(f"Max MOS-LQO: {max(scores):.6f}")


if __name__ == '__main__':
    main()
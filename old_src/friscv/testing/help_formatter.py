import argparse


class TestingHelpFormatter(argparse.HelpFormatter):
    def _format_usage(self, usage, actions, groups, prefix):
        return """Usage: python script.py [OPTIONS]

        A utility for processing and simulating files with Vivado.
        
        File Selection Options:
          -a, --all            Process all files with appropriate extension in current directory
                               (default if no selection method is specified)
          -d DIR, --dir DIR    Process all files with appropriate extension in specified directory
          -f FILE [FILE ...], --file FILE [FILE ...]
                               Process specific file(s)
        
        Processing Options:
          -s, --sequential     Run simulations sequentially instead of in parallel
          -p N, --parallel N   Run up to N simulations in parallel (cannot be used with -s)
          -b, --binary         Process binary (.b) files directly instead of intermediate (.e) files
        
        General Options:
          -h, --help           Show this help message and exit
        
        Description:
          This script automates the process of converting intermediate files to binary format
          and running simulations with Vivado. It checks for Vivado installation, creates
          temporary directories, processes the selected files, and displays simulation results
          in a tabular format.
        
          When using intermediate files (.e), the script first converts them to binary format
          before simulation. When using binary files (.b), it runs simulations directly.
        
          Results are displayed with PASS/FAIL status for each processed file.
        
        Examples:
          python script.py                    # Process all .e files in current directory
          python script.py -a                 # Same as above
          python script.py -d tests/          # Process all .e files in tests/ directory
          python script.py -f test1.e test2.e # Process only specified files
          python script.py -b                 # Process all .b files in current directory
          python script.py -s -f test1.e      # Process test1.e sequentially
          python script.py -p 2 -f test1.e test2.e test3.e # Process files with max 2 parallel simulations
        """

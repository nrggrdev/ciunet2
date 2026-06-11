import sys
import os

# Add project root to sys.path so ciunet/daq_net/python_util packages can be found
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ciunet import main as main_


def run(): main_.main()


if __name__ == '__main__':
    run()

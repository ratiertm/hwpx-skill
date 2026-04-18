"""Allow ``python -m pyhwpxlib`` to invoke the CLI."""
import sys

if len(sys.argv) > 1 and sys.argv[1] == "guide":
    from pyhwpxlib.llm_guide import print_guide
    print_guide()
else:
    from pyhwpxlib.cli import main
    main()

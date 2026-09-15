import argparse
import base64
import json
import sys
import os
import requests
from requests.auth import HTTPBasicAuth

def main():
    """
    Main function to parse arguments and interact with the NGPsuite API.
    """
    parser = argparse.ArgumentParser(
        description="A command-line client for the NGPsuite API.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "image_path",
        help="Path to the input image file (PNG or JPG)."
    )
    parser.add_argument(
        "--hpo",
        metavar="\"HP:0001,HP:0002,...\"",
        help="Optional: A comma-separated string of HPO IDs."
    )
    parser.add_argument(
        "--url",
        default="https://localhost/api/predict",
        help="URL of the backend API endpoint.\n(default: https://localhost/api/predict)"
    )
    parser.add_argument(
        "--user",
        default="your_username",
        help="Username for API authentication.\n(default: your_username)"
    )
    parser.add_argument(
        "--password",
        default="your_password",
        help="Password for API authentication.\n(default: your_password)"
    )
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="Disable SSL certificate verification. Use for self-signed certificates on localhost."
    )

    args = parser.parse_args()

    # --- 1. Validate and read the image file ---
    if not os.path.isfile(args.image_path):
        print(f"Error: Image file not found at '{args.image_path}'", file=sys.stderr)
        sys.exit(1)

    try:
        with open(args.image_path, "rb") as image_file:
            # Encode image to Base64 and decode to a UTF-8 string for the JSON payload
            image_b64 = base64.b64encode(image_file.read()).decode('utf-8')
    except IOError as e:
        print(f"Error: Could not read image file: {e}", file=sys.stderr)
        sys.exit(1)

    # --- 2. Construct the JSON payload ---
    payload = {
        "img": image_b64
    }
    if args.hpo:
        # Split the comma-separated string into a list of HPO IDs
        hpo_ids = [hpo_id.strip() for hpo_id in args.hpo.split(',')]
        payload["hpo_ids"] = hpo_ids

    # --- 3. Make the API request ---
    try:
        print("Sending request to API...", file=sys.stderr)
        response = requests.post(
            args.url,
            json=payload,
            auth=HTTPBasicAuth(args.user, args.password),
            # Disable SSL verification if --no-verify is used
            verify=not args.no_verify,
            timeout=120 # Set a timeout of 120 seconds
        )
        # Raise an exception for HTTP error codes (4xx or 5xx)
        response.raise_for_status()

        # --- 4. Print the successful response to standard output ---
        # Pretty-print the JSON with an indent of 2 spaces
        print(json.dumps(response.json(), indent=2))

    except requests.exceptions.RequestException as e:
        print(f"\nError: API request failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

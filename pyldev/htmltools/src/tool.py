import sys, os


def generate_homepage(input_dir: str, output_path: str = "home.html"):
    """
    Generate a homepage that creates links to redirect to subfolders.
    """

    if not os.path.isdir(input_dir):
        print(f"Pipeline >> Widoco directory not found: {input_dir}")
        return None

    # Get all subdirectories (objects)
    objects = [
        d for d in os.listdir(input_dir) if os.path.isdir(os.path.join(input_dir, d))
    ]
    objects.sort()  # Sort alphabetically

    # Generate HTML content
    html_content = f"""<!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>App title</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                h1 {{
                    color: #2c3e50;
                    border-bottom: 2px solid #eee;
                    padding-bottom: 10px;
                }}
                .objects-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
                    gap: 20px;
                    margin-top: 30px;
                }}
                .object-card {{
                    border: 1px solid #ddd;
                    border-radius: 5px;
                    padding: 15px;
                    transition: transform 0.2s, box-shadow 0.2s;
                }}
                .object-card:hover {{
                    transform: translateY(-5px);
                    box-shadow: 0 10px 20px rgba(0,0,0,0.1);
                }}
                .object-name {{
                    font-size: 1.2em;
                    font-weight: bold;
                    margin-bottom: 10px;
                }}
                .object-link {{
                    display: inline-block;
                    margin-top: 10px;
                    background-color: #3498db;
                    color: white;
                    padding: 8px 15px;
                    text-decoration: none;
                    border-radius: 4px;
                }}
                .object-link:hover {{
                    background-color: #2980b9;
                }}
                .footer {{
                    margin-top: 50px;
                    text-align: center;
                    font-size: 0.9em;
                    color: #7f8c8d;
                }}
            </style>
        </head>
        <body>
            <h1>App title</h1>
            <p>Select a page to browse</p>

            <div class="objects-grid">
        """

    # Add a card for each object
    for obj in objects:
        html_content += f"""
            <div class="object-card">
                <div class="object-name">{obj}</div>
                <a href="/{obj}" class="object-link">Browse pages</a>
            </div>
            """

    # Change the footer
    html_content += f"""
        </div>
        <div class="footer">
            <p>PyYel DevOps - All rights reserved.</p> 
        </div>
    </body>
    </html>
    """

    with open(output_path, "w") as f:
        f.write(html_content)

    return None

"""
Battery Icon Generator
Generates normal and alert battery icons for the system tray notification.
"""

from PIL import Image, ImageDraw
import os


def create_battery_icon(
    filename,
    size=(64, 64),
    battery_color="#00AA00",
    fill_level=0.9,
    show_alert=False
):
    """
    Create a battery icon with specified parameters.

    Args:
        filename: Output filename path
        size: Tuple of (width, height) in pixels
        battery_color: Hex color code for the battery
        fill_level: Float between 0 and 1 representing charge level
        show_alert: Boolean to show warning symbol
    """
    # Create a new image with transparency
    img = Image.new('RGBA', size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    width, height = size

    # Battery dimensions (with padding)
    padding = 8
    battery_width = width - (2 * padding)
    battery_height = height - (2 * padding) - 4  # Extra space for terminal

    # Battery body position
    battery_x = padding
    battery_y = padding + 4  # Offset for terminal

    # Terminal (nub on top-right)
    terminal_width = 12
    terminal_height = 4
    terminal_x = battery_x + battery_width - terminal_width - 4
    terminal_y = padding

    # Draw terminal
    draw.rounded_rectangle(
        [terminal_x, terminal_y, terminal_x + terminal_width, terminal_y + terminal_height],
        radius=2,
        fill=battery_color,
        outline=battery_color
    )

    # Draw battery body outline
    outline_width = 2
    draw.rounded_rectangle(
        [battery_x, battery_y, battery_x + battery_width, battery_y + battery_height],
        radius=4,
        fill=None,
        outline=battery_color,
        width=outline_width
    )

    # Draw battery fill level
    fill_padding = 4
    fill_x = battery_x + fill_padding
    fill_y = battery_y + fill_padding
    fill_width = battery_width - (2 * fill_padding)
    fill_height = battery_height - (2 * fill_padding)

    # Calculate fill based on level
    actual_fill_height = int(fill_height * fill_level)
    fill_y_start = fill_y + (fill_height - actual_fill_height)

    if fill_level > 0:
        draw.rounded_rectangle(
            [fill_x, fill_y_start, fill_x + fill_width, fill_y + fill_height],
            radius=2,
            fill=battery_color
        )

    # Draw alert symbol if needed
    if show_alert:
        # Draw exclamation mark in the center
        symbol_x = width // 2
        symbol_y = height // 2

        # Exclamation mark (!)
        # Top part (line)
        draw.rectangle(
            [symbol_x - 2, symbol_y - 10, symbol_x + 2, symbol_y + 2],
            fill='white'
        )
        # Bottom part (dot)
        draw.ellipse(
            [symbol_x - 2, symbol_y + 5, symbol_x + 2, symbol_y + 9],
            fill='white'
        )

    # Save the icon
    img.save(filename, 'PNG')
    print(f"Created: {filename}")


def main():
    """Generate both battery icons."""
    # Ensure assets directory exists
    assets_dir = os.path.join(os.path.dirname(__file__), 'assets')
    os.makedirs(assets_dir, exist_ok=True)

    # Icon paths
    normal_icon_path = os.path.join(assets_dir, 'icon.png')
    alert_icon_path = os.path.join(assets_dir, 'icon_alert.png')

    print("Generating battery icons...")
    print("-" * 50)

    # Generate normal battery icon (green, 90% full)
    create_battery_icon(
        filename=normal_icon_path,
        size=(64, 64),
        battery_color="#00AA00",
        fill_level=0.9,
        show_alert=False
    )

    # Generate alert battery icon (red, 15% full, with warning)
    create_battery_icon(
        filename=alert_icon_path,
        size=(64, 64),
        battery_color="#DD0000",
        fill_level=0.15,
        show_alert=True
    )

    print("-" * 50)
    print("Icon generation complete!")
    print(f"\nGenerated files:")
    print(f"  - {os.path.abspath(normal_icon_path)}")
    print(f"  - {os.path.abspath(alert_icon_path)}")


if __name__ == "__main__":
    main()

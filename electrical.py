import math
import sys


def analyze_dc(voltage_v, resistance_ohm):
    """Analyze a simple DC circuit using Ohm's law.

    Args:
        voltage_v: Voltage in volts
        resistance_ohm: Resistance in ohms

    Returns:
        Dictionary with current in amperes and power in watts.

    Raises:
        ValueError: If the input is invalid or resistance is zero.
    """
    try:
        voltage = float(voltage_v)
        resistance = float(resistance_ohm)
    except (TypeError, ValueError) as exc:
        raise ValueError("Voltage and resistance must be numeric values.") from exc

    if not math.isfinite(voltage) or not math.isfinite(resistance):
        raise ValueError("Voltage and resistance must be finite numbers.")

    if resistance == 0:
        raise ValueError("Resistance cannot be zero in a DC circuit.")

    current_a = voltage / resistance
    power_w = voltage * current_a

    return {"current_a": current_a, "power_w": power_w}


def main():
    """Run the DC circuit calculation from the command line."""
    if len(sys.argv) > 1:
        if len(sys.argv) != 3:
            print("Usage: python electrical.py <voltage_v> <resistance_ohm>")
            sys.exit(1)
        try:
            result = analyze_dc(sys.argv[1], sys.argv[2])
        except ValueError as exc:
            print(f"Error: {exc}")
            sys.exit(1)
    else:
        try:
            voltage_v = input("Voltage (V): ")
            resistance_ohm = input("Resistance (ohm): ")
            result = analyze_dc(voltage_v, resistance_ohm)
        except ValueError as exc:
            print(f"Error: {exc}")
            sys.exit(1)

    print(f"Current = {result['current_a']:.3f} A")
    print(f"Power = {result['power_w']:.3f} W")


if __name__ == "__main__":
    main()

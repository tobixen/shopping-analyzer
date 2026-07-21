"""Main menu interface for the shopping analyzer."""

from workflows import initial_setup, refresh_data, update_data


def main() -> None:
    """
    Main function that provides a simple menu for choosing between
    initial setup and update modes.
    """
    print("=== Willkommen, welche Kassenbons möchtest du hinzufügen? ===")
    print("1. Initial Setup (Alle Kassenbons)")
    print("2. Update (Nur neue Kassenbons hinzufügen)")
    print("3. Refresh (Vorhandene Kassenbons neu parsen)")
    print("4. Beenden")

    while True:
        try:
            choice = input("\nWähle eine Option (1-4): ").strip()

            if choice == "1":
                print("\nStarte Initial Setup...")
                success = initial_setup()
                if success:
                    print("✓ Initial Setup erfolgreich abgeschlossen!")
                else:
                    print("✗ Initial Setup fehlgeschlagen!")
                break

            elif choice == "2":
                print("\nStarte Update...")
                success = update_data()
                if success:
                    print("✓ Update erfolgreich abgeschlossen!")
                else:
                    print("✗ Update fehlgeschlagen!")
                break

            elif choice == "3":
                print("\nStarte Refresh...")
                success = refresh_data()
                if success:
                    print("✓ Refresh erfolgreich abgeschlossen!")
                else:
                    print("✗ Refresh fehlgeschlagen!")
                break

            elif choice == "4":
                print("Auf Wiedersehen!")
                break

            else:
                print("Ungültige Eingabe. Bitte wähle 1, 2, 3 oder 4.")

        except KeyboardInterrupt:
            print("\n\nProgramm unterbrochen.")
            break
        except Exception as e:
            print(f"Ein Fehler ist aufgetreten: {e}")
            break

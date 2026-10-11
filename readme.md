# Shopping Analyzer

A Python tool to automatically extract and manage Lidl receipt data from your online purchase history.

Ein Python-Tool zum automatischen Extrahieren und Verwalten von Lidl-Kassenbondaten aus Ihrem Online-Kaufverlauf.

---

> [!Important] 
> **📹 YouTube Video Update Notice**
>
> If you came here from a YouTube video, please note: The setup process has **changed** from the video instructions. This tool now uses an **API** instead of web scraping, making it more reliable and faster.
>
> **Please follow the instructions in this README below** instead of the video tutorial, as the old web scraping method is no longer used.

---

## 🇬🇧 English

### Features

- **Secure Login**: Prompts you to enter your Lidl credentials securely when running
- **Receipt Extraction**: Downloads all receipt data including items, prices, and dates
- **Smart Updates**: Only downloads new receipts during updates (no duplicates)
- **Data Export**: Saves all data in JSON format for easy analysis
- **Interactive Menu**: User-friendly interface for easy operation

### Prerequisites

- [Python 3.7 or higher](https://www.python.org/downloads/)
- [Google Chrome browser](https://www.google.com/chrome/) or [Mozilla Firefox browser](https://www.mozilla.org/firefox/) installed
- Lidl Plus account with online purchase history

### Important Limitation

⚠️ **Data Availability**: Receipt data on the Lidl website is only available from **February 2023 onwards**. The script will automatically stop when it encounters receipts older than February 2023, as this data is no longer accessible on the Lidl website.

### Installation

1. **Clone or download this repository**

   ```bash
   git clone <repository-url>
   cd shopping-analyzer
   ```

   Or download the ZIP file from GitHub and extract it.

2. **Open the folder in a terminal**

   Navigate to the project folder using your preferred terminal (e.g., Terminal on macOS, Command Prompt on Windows, or any terminal of your choice like Warp).

3. **Create a virtual environment (recommended)**

   This ensures that the packages we install only affect this project and don't clutter your entire system:

   ```bash
   python -m venv venv
   ```

4. **Activate the virtual environment**

   **On Mac/Linux:**

   ```bash
   source venv/bin/activate
   ```

   **On Windows:**

   ```cmd
   venv\Scripts\activate
   ```

5. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

Now the project is successfully set up and you can start extracting data from your Lidl+ account!

### Usage

**Step 1: Choose your authentication method**

> [!WARNING] 
> **🔐 Security Notice**: This tool requires access to your Lidl Plus account cookies to function. Please be aware of the following security considerations:
>
> - **Cookie files contain sensitive authentication data** that can grant access to your Lidl Plus account
> - **Never share your `lidl_cookies.json` file** with others or commit it to version control (Git)
> - **Store cookie files securely** and delete them when no longer needed
> - The automatic browser extraction is generally more secure as cookies are extracted temporarily from memory

You have two options for authentication:

**Option A: Automatic Browser Cookie Extraction (Recommended)**

- Login to Lidl Plus in Firefox or Chrome and keep the browser open
- [Lidl Login](https://www.lidl.de/mla/)
- ⚠️ **Note for macOS users**: Chrome may not work due to keychain access restrictions. If you encounter a "key for cookie decryption" error, please use Firefox instead, which works more reliably on macOS.

**Option B: Manual Cookie File**

> [!CAUTION] 
> **⚠️ Security Risk**: Manually exporting and storing cookies in a file poses additional security risks:
>
> - The `lidl_cookies.json` file will contain your authentication tokens in plain text
> - Anyone with access to this file can access your Lidl Plus account
> - Ensure the file has appropriate permissions and is stored in a secure location
> - Delete the file immediately after use if possible
> - **Never upload this file to cloud storage, GitHub, or share it with anyone**

- Export cookies using a browser extension like [EditThisCookie](https://chromewebstore.google.com/detail/editthiscookie-v3/ojfebgpkimhlhcblbalbfjblapadhbol?hl=de&utm_source=ext_sidebar)
- Save them to a file named `lidl_cookies.json`

**Step 2: Run the data extraction script**

```bash
python get_data.py
```

**Step 3: Choose your operation mode**

You'll see a menu with options:

1. Initial Setup - Extract all historical receipt data (choose this for first run)
2. Update Data - Add only new receipts
3. Refresh - Re-fetch and re-parse the receipts already in your JSON file (see
   [Totals and discounts](#totals-and-discounts))
4. Exit

The same refresh is available as a command:

```bash
python get_data.py refresh --browser chromium
```

**Step 4: Choose your authentication method**

Choose how you want to authenticate:

1. Firefox (automatic cookie extraction)
2. Chrome (automatic cookie extraction)
3. Cookie File (manual - using `lidl_cookies.json`)

If you chose option 3, make sure you have created a `lidl_cookies.json` file first.

**Step 5: Automated data extraction**

The program will automatically extract data from all your receipts (after 14.02.2022)

⚠️ **Important**: This process may take some time, so grab a coffee or take a short walk! If the process crashes for any reason, simply run it again - the program will resume from where it left off.

**For future updates**: When you want to add new receipts later, run `python get_data.py` again and choose option 2 (Update Data). This will only extract new receipts that aren't already in your data.

### Output

The script creates a `lidl_receipts.json` file containing all your receipt data, automatically sorted by date (newest first).

#### Totals and discounts

> [!IMPORTANT]
> **`total_price` is the amount actually charged — net of all discounts.**
> If you want the figure *before* discounts, read `total_price_gross`.

Receipts print each discount on its own line, directly below the article it
reduces. Those lines are parsed and attached to the item they belong to:

| Field | Meaning |
| --- | --- |
| `total_price` | What the card was charged (gross − discounts) |
| `total_price_gross` | Sum of the printed line totals, before discounts |
| `total_price_no_saving` | Alias of `total_price_gross`, kept for compatibility |
| `total_price_source` | Where `total_price` came from, for auditing |
| `discount_total` | All discounts on the receipt |
| `lidlplus_saved_amount` | The Lidl Plus coupon share of that |
| `sticker_discount_amount` | The in-store markdown share of that |

Each item additionally carries `line_total`, `net_total`, `discount_total` and
a `discounts` list. Every discount records its `amount`, `label`,
`promotion_id` and a `type`:

- **`lidlplus_coupon`** — a Lidl Plus app coupon. These are what the receipt
  footer totals up as "X EUR gespart" / "Ти спести X с Lidl Plus".
- **`markdown`** — an in-store reduction sticker (short shelf life, damaged
  packaging). *Not* a Lidl Plus saving and not part of that footer total.

The two are kept apart because they behave differently: coupons are tied to a
campaign, markdowns to the individual physical item.

> [!NOTE]
> Receipts collected before discount parsing existed recorded the gross total
> as `total_price`. Lidl keeps receipts retrievable long after purchase, so
> those records can be rebuilt in place with `python get_data.py refresh`.

### Data Analysis Dashboard

After collecting your receipt data, you can view and analyze it using the interactive dashboard:

```bash
streamlit run dashboard.py
```

This will start a web-based dashboard accessible at `http://localhost:8501` where you can analyse your shopping history.

---

## 🇩🇪 Deutsch

### Funktionen

- **Sicherer Login**: Fordert Sie zur sicheren Eingabe Ihrer Lidl-Zugangsdaten beim Ausführen auf
- **Kassenbon-Extraktion**: Lädt alle Kassenbondaten inklusive Artikel, Preise und Daten herunter
- **Intelligente Updates**: Lädt nur neue Kassenbons bei Updates herunter (keine Duplikate)
- **Datenexport**: Speichert alle Daten im JSON-Format für einfache Analyse
- **Interaktives Menü**: Benutzerfreundliche Oberfläche für einfache Bedienung

### Voraussetzungen

- [Python 3.7 oder höher](https://www.python.org/downloads/)
- [Google Chrome browser](https://www.google.com/chrome/) oder [Mozilla Firefox Browser](https://www.mozilla.org/firefox/) installiert
- Lidl Plus Konto mit Online-Kaufverlauf

### Wichtige Einschränkung

⚠️ **Datenverfügbarkeit**: Kassenbondaten sind auf der Lidl-Website nur ab **Februar 2023** verfügbar. Das Skript stoppt automatisch, wenn es auf ältere Kassenbons stößt, da diese Daten nicht mehr auf der Lidl-Website zugänglich sind.

### Installation

**Schritt-für-Schritt Anleitung:**

1. **Repository herunterladen**

   Laden Sie das Repository von GitHub herunter oder klonen Sie es mit git (falls Sie damit Erfahrung haben):

   ```bash
   git clone <repository-url>
   cd shopping-analyzer
   ```

   Alternativ können Sie die ZIP-Datei herunterladen und entpacken.

2. **Ordner im Terminal öffnen**

   Öffnen Sie den Projektordner in einem Terminal Ihrer Wahl (z.B. "warp" unter macOS, aber jedes Terminal funktioniert).

3. **Python Environment aufsetzen**

   Dies sorgt dafür, dass die Packages nur dieses Projekt beeinflussen und nicht Ihren ganzen Computer:

   ```bash
   python -m venv venv
   ```

4. **Environment aktivieren**

   **Unter Mac/Linux:**

   ```bash
   source venv/bin/activate
   ```

   **Unter Windows:**

   ```cmd
   venv\Scripts\activate
   ```

5. **Benötigte Packages installieren**

   ```bash
   pip install -r requirements.txt
   ```

Jetzt ist das Projekt erfolgreich aufgesetzt und Sie können anfangen, Ihre Daten aus Ihrem Lidl+ Account zu ziehen!

### Verwendung

**Schritt 1: Authentifizierungsmethode wählen**

> [!WARNING] 
> **🔐 Sicherheitshinweis**: Dieses Tool benötigt Zugriff auf Ihre Lidl Plus Account-Cookies, um zu funktionieren. Bitte beachten Sie folgende Sicherheitsaspekte:
>
> - **Cookie-Dateien enthalten sensible Authentifizierungsdaten**, die Zugriff auf Ihr Lidl Plus Konto gewähren können
> - **Teilen Sie Ihre `lidl_cookies.json` Datei niemals** mit anderen oder laden Sie sie in eine Versionsverwaltung (Git) hoch
> - **Speichern Sie Cookie-Dateien sicher** und löschen Sie sie, wenn sie nicht mehr benötigt werden
> - Die automatische Browser-Extraktion ist generell sicherer, da Cookies nur temporär aus dem Speicher extrahiert werden

Sie haben zwei Möglichkeiten zur Authentifizierung:

**Option A: Automatische Browser-Cookie-Extraktion (Empfohlen)**

- Im Browser (Firefox oder Chrome) bei Lidl+Plus anmelden und den Browser geöffnet lassen
- [Lidl Login](https://www.lidl.de/mla/)
- ⚠️ **Hinweis für macOS-Nutzer**: Chrome funktioniert möglicherweise nicht aufgrund von Schlüsselbund-Zugriffsbeschränkungen. Falls ein "key for cookie decryption"-Fehler auftritt, verwenden Sie bitte Firefox, welcher auf macOS zuverlässiger funktioniert.

**Option B: Manuelle Cookie-Datei (Alternative)**

> [!CAUTION] 
> **⚠️ Sicherheitsrisiko**: Das manuelle Exportieren und Speichern von Cookies in einer Datei birgt zusätzliche Sicherheitsrisiken:
>
> - Die `lidl_cookies.json` Datei enthält Ihre Authentifizierungstokens im Klartext
> - Jeder mit Zugriff auf diese Datei kann auf Ihr Lidl Plus Konto zugreifen
> - Stellen Sie sicher, dass die Datei angemessene Berechtigungen hat und an einem sicheren Ort gespeichert wird
> - Löschen Sie die Datei nach Möglichkeit sofort nach der Verwendung
> - **Laden Sie diese Datei niemals in Cloud-Speicher, GitHub hoch oder teilen Sie sie mit anderen**

- Exportieren Sie Cookies mit einer Browser-Erweiterung wie [EditThisCookie](https://chromewebstore.google.com/detail/editthiscookie-v3/ojfebgpkimhlhcblbalbfjblapadhbol?hl=de&utm_source=ext_sidebar)
- Speichern Sie diese in einer Datei namens `lidl_cookies.json`

**Schritt 2: Datenextraktions-Skript starten**

```bash
python get_data.py
```

**Schritt 3: Betriebsmodus wählen**

Sie haben die Wahl zwischen:

1. Initial Setup - Alle historischen Kassenbondaten extrahieren (für den ersten Durchlauf)
2. Update Data - Nur neue Kassenbons hinzufügen
3. Refresh - Vorhandene Kassenbons neu abrufen und parsen
4. Exit - Beenden

Wählen Sie "1" für das Initial Setup und bestätigen Sie mit der Enter-Taste.

**Schritt 4: Authentifizierungsmethode wählen**

Wählen Sie aus, wie Sie sich authentifizieren möchten:

1. Firefox (automatische Cookie-Extraktion)
2. Chrome (automatische Cookie-Extraktion)
3. Cookie-Datei (manuell - verwendet `lidl_cookies.json`)

Wenn Sie Option 3 wählen, stellen Sie sicher, dass Sie zuerst eine `lidl_cookies.json` Datei erstellt haben.

**Schritt 5: Automatische Datenextraktion**

Nun wird das Programm automatisiert die Daten all Ihrer Kassenbons (nach dem 14.02.2022) extrahieren

⚠️ **Wichtiger Hinweis**: Dieser Prozess kann etwas dauern - holen Sie sich einen Kaffee oder gehen Sie eine kleine Runde spazieren! Sollte der Prozess aus irgendeinem Grund abstürzen, ist das kein Problem. Wiederholen Sie das Ganze einfach - das Programm springt schnell wieder zu der Stelle, wo es aufgehört hat.

**Für künftige Updates**: Wenn Sie Ihre Daten in Zukunft updaten möchten (weil neue Kassenbons hinzugekommen sind), führen Sie einfach wieder `python get_data.py` aus und wählen Sie Option 2. Hierbei werden nur die neuesten, noch nicht vorhandenen Kassenbons extrahiert und zu Ihren Daten hinzugefügt.

### Ausgabe

Nachdem der Prozess abgeschlossen ist, finden Sie alle extrahierten Daten in der `lidl_receipts.json` Datei. Diese Datei enthält alle Ihre Kassenbondaten, automatisch nach Datum sortiert (neueste zuerst), und ist gleichzeitig die Datenquelle für das Dashboard.

#### Summen und Rabatte

> [!IMPORTANT]
> **`total_price` ist der tatsächlich belastete Betrag — abzüglich aller Rabatte.**
> Für den Betrag *vor* Rabatten steht `total_price_gross` zur Verfügung.

Kassenbons drucken jeden Rabatt in einer eigenen Zeile, direkt unter dem
Artikel, den er reduziert. Diese Zeilen werden ausgewertet und dem
zugehörigen Artikel zugeordnet:

| Feld | Bedeutung |
| --- | --- |
| `total_price` | Tatsächlich belasteter Betrag (brutto − Rabatte) |
| `total_price_gross` | Summe der gedruckten Zeilensummen, vor Rabatten |
| `total_price_no_saving` | Alias von `total_price_gross`, aus Kompatibilitätsgründen |
| `total_price_source` | Herkunft von `total_price`, zur Nachvollziehbarkeit |
| `discount_total` | Alle Rabatte des Kassenbons |
| `lidlplus_saved_amount` | Davon der Anteil der Lidl Plus Coupons |
| `sticker_discount_amount` | Davon der Anteil der Rabattaufkleber |

Jeder Artikel enthält zusätzlich `line_total`, `net_total`, `discount_total`
sowie eine `discounts`-Liste. Jeder Rabatt speichert `amount`, `label`,
`promotion_id` und einen `type`:

- **`lidlplus_coupon`** — ein Lidl Plus Coupon. Diese ergeben zusammen den
  Betrag in der Fußzeile ("X EUR gespart").
- **`markdown`** — ein Rabattaufkleber im Markt (kurzes MHD, beschädigte
  Verpackung). *Keine* Lidl Plus Ersparnis und nicht Teil dieser Fußzeile.

Beide werden getrennt geführt, da sie sich unterschiedlich verhalten: Coupons
hängen an einer Kampagne, Rabattaufkleber am einzelnen physischen Artikel.

> [!NOTE]
> Kassenbons, die vor der Rabattauswertung gesammelt wurden, enthielten den
> Bruttobetrag als `total_price`. Da Lidl Kassenbons noch lange nach dem Kauf
> bereitstellt, lassen sich diese Datensätze mit `python get_data.py refresh`
> neu aufbauen.

### Datenanalyse-Dashboard

Nach dem Sammeln Ihrer Kassenbondaten können Sie diese mit dem interaktiven Dashboard anzeigen und analysieren.

**Dashboard starten:**

```bash
streamlit run dashboard.py
```

Anschließend können Sie über den Link auf Ihr Dashboard zugreifen. Dies startet ein webbasiertes Dashboard, das unter `http://localhost:8501` erreichbar ist.

---

## 📄 License

This project is licensed under the **GNU Affero General Public License v3.0** (AGPL-3.0).

### Copyright Notice

```text
Shopping Analyzer - Tool to extract and manage Lidl receipt data
Copyright (C) 2025 Lukas Weihrauch

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
```

### What this means for you:

- **Freedom to use**: You can use this software for any purpose
- **Freedom to study**: You can examine how the program works and adapt it to your needs
- **Freedom to share**: You can redistribute copies to help others
- **Freedom to improve**: You can distribute copies of your modified versions to benefit the community

### Important AGPL-3.0 Requirements:

- **Network use = Source sharing**: If you run a modified version of this software on a server that others can access over a network, you must make the source code of your modified version available to those users
- **Share improvements**: Any modifications or derivative works must also be licensed under AGPL-3.0
- **Attribution**: You must preserve all copyright notices and license information

For the complete license terms, see the [`LICENCE.md`](./LICENCE.md) file in this repository.

---

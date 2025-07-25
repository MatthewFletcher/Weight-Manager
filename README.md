# Weight Entry System

A simple, foolproof, local-only app for tracking names, room numbers, and up to 5 weights per person, with PDF export.  
Built with Python, FastAPI, HTML, and Docker.  
**No cloud, no network required—runs entirely on your Windows/Mac/Linux computer.**

---

## Features

- Enter new people with name, room number, and weight.
- Add additional weights for existing people (up to 5 per person, most recent always shown).
- See all entries in a sortable table. 
- Add weights or delete entries with just a few clicks.
- “Select all” and shift+click support for mass selection.
- Aligned display of weights for easy comparison.
- Help popups on each page, with instructions loaded from markdown files.
- Generate a PDF report showing all names, rooms, and the latest weight.
- All data is saved locally—no internet required!

---

## Getting Started

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop) installed on your computer.

### Quick Start

1. **Clone this repository:**
    ```sh
    git clone https://github.com/yourusername/weight-entry-system.git
    cd weight-entry-system
    ```

2. **Build and run the app using Docker Compose:**
    ```sh
    docker-compose up --build
    ```
    *(Or use `docker compose up --build` on newer Docker installs.)*

3. **Open your browser to** [http://localhost:6900](http://localhost:6900)

4. **To stop the app:**  
    Press `Ctrl+C` in the terminal and run `docker-compose down` if needed.

---

## Usage

- Use the **Weight Entry Form** to add new people.
- Use **View All Entries** to see, sort, and update weights.
- Click the `?` button on any page for a detailed help popup.
- Use the checkbox at the top left to select/deselect all entries, and use shift+click to select a range.
- Click **Generate PDF Report** to create and download a printable table.

---

## Customizing Help Pages

- Help content is stored as markdown files in the `help/` directory.
- Edit these `.md` files to update help popups instantly—no need to rebuild the app.

---

## Directory Structure
```
.
├── app.py # Main FastAPI application
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── static/ # CSS and JavaScript files
├── templates/ # HTML templates (Jinja2)
├── help/ # Markdown files for page-specific help popups
└── ... # Other files
```
# My Learning Vault

#### Video Demo:  https://youtu.be/f7ReU5I-7tU

#### Description:
My Learning Vault is a web application designed to organize study material in a structured, searchable, and visually cleaner way. The idea came from a real problem: when taking long courses with modules, lessons, markdown notes, and supporting files, the material usually ends up scattered across local folders. The goal of this project was to turn that workflow into a single web experience that is easier to navigate, easier to search, and more pleasant to use.

The application follows a clear and opinionated hierarchy. Each course contains modules, each module contains lessons, and each lesson contains one main markdown note plus an optional supporting attachment. This was an intentional product decision. Instead of trying to build a fully generic note editor in the first version, the project focuses on a format that matches the way long-form courses and professional trainings are usually studied in practice. That makes the interface easier to understand and keeps the product aligned with its actual use case.

The home page works as a course library. From there, the user can create a course manually or import an entire folder that already follows the local study structure. The importer accepts a directory layout in which the top-level folder represents the course, the first nested folders represent modules, the next level represents lessons, and each lesson can include an `anotacoes.md` file. This feature was built to reuse a real study method instead of forcing the user to rebuild everything manually inside the system. The import process also ignores hidden and technical paths such as `.git`, preventing repository noise from becoming lesson content.

Once the user enters a course, the experience no longer jumps between separate pages for modules and lessons. The main workflow happens inside a single screen. On the left, modules are shown as an accordion and each module reveals its lessons. On the right, the selected lesson is opened immediately, without a page reload. This decision gives the application more of a course-platform or digital notebook feel, instead of looking like a traditional CRUD admin panel.

Lesson content is based on markdown. In view mode, the markdown is rendered into a more readable format; in edit mode, the user can keep writing in raw markdown. That format was chosen because it is portable, durable, simple, and especially useful for technical notes. In addition, each lesson can include one uploaded supporting file. Attachments are displayed in a dedicated visual card so they feel like part of the lesson rather than a raw link dumped into the interface.

Search is another central feature of the project. There is a global search that can find terms in course titles, module titles, lesson titles, and lesson notes. When the user opens a result, the interface loads the correct lesson, highlights the searched term inside the note, and scrolls toward the first occurrence. This removes the need to manually search inside long notes and turns the product into a much more useful reference tool after the study session is over.

The application also includes drag-and-drop ordering. Modules can be reordered freely, and lessons can be reordered within their own module. This matters because a real study process changes over time, and the tool needs to support reorganization without forcing the user to recreate content. To keep the interface cleaner, the old visible configuration panel was replaced with context menus triggered by right-click, which still expose important actions such as adding modules, adding lessons, and deleting items without cluttering the layout.

From a technical perspective, the project was built with Flask on the backend and SQLite as the local database. Flask handles the routes, templates, forms, attachment uploads, and import logic. SQLite stores the main structure of the product: courses, modules, and lessons. The frontend uses server-rendered Jinja templates plus JavaScript for interactions that should happen without reloads, such as expanding modules, switching between view and edit modes, saving lessons inline, opening confirmation modals, and persisting drag-and-drop ordering.

Main project files:

- `app.py`: contains the Flask application, database configuration, routes, import logic, attachment upload handling, search, reordering, and inline actions.
- `schema.sql`: defines the main database tables.
- `requirements.txt`: lists the Python dependencies needed to run the project.
- `templates/layout.html`: defines the shared page shell.
- `templates/index.html`: renders the course library and the modal used to create or import courses.
- `templates/course_detail.html`: renders the main single-screen course experience with modules, lessons, markdown notes, context menus, and drag and drop.
- `templates/search.html`: renders the global search results.
- `static/styles.css`: contains the visual system, layout, responsive behavior, and component styling.

## How to run locally

To clone the repository:

```bash
git clone <REPOSITORY_URL>
cd my-learning-vault
```

To create the virtual environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

To start the application locally:

```bash
flask --app app --debug run
```

Then open:

```text
http://127.0.0.1:5000
```

When the application starts, it creates and uses the local `vault.db` file. Uploaded lesson attachments are stored in the `uploads/` directory.

One of the most important design decisions was to avoid the default look of a generic SaaS dashboard. The interface was refined to feel closer to a dark members-area or study platform, with emphasis on reading, organization, and retrieval. Another important choice was replacing native browser confirmations with custom confirmation modals that match the rest of the application and avoid abrupt visual interruptions.

There are several possible future improvements, such as support for multiple attachments per lesson, tags, more advanced filters, progress tracking, and smarter synchronization with external sources. But for this version, the focus was to deliver a strong and useful MVP: a digital course notebook with a real structure, folder import, markdown-based notes, search, attachments, and a fluid single-screen navigation model.

In summary, My Learning Vault was not designed only as an academic assignment. It was built as the beginning of a real tool for organizing knowledge gathered through courses, trainings, and long study tracks. That goal influenced both the technical decisions and the interface decisions throughout the project.

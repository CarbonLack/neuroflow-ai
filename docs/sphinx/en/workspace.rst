Using the workspace
===================

The center shows the current analysis, the left rail selects modules, and the right panel contains the assistant, help, and logs.
Selecting a module or Next changes the page. **Run selected analysis** at the bottom starts computation.

Find an action
--------------

Press **Ctrl+K** and type a task, module, or control name. Use the arrow keys to select a result and Enter to open it.
Unavailable actions explain their prerequisites. **File → Recent projects** and the home page reopen previous projects;
entries whose files have moved are disabled.

File manages projects; Edit opens figure, AI, and sorter settings; View controls layout; Analysis runs tasks; Help opens guides.
The full workflow remains available in Analysis. You can run individual modules as needed.

Arrange the columns
-------------------

* **Ctrl+B** compacts the workflow rail. Narrow windows compact it automatically.
* **Ctrl+J** shows or hides the assistant. All three columns can stay open; drag their separators to resize them.
* **Plot tools** expands plot style, panel selection, editing, export, and trace controls. Collapsing this section gives plots more space.
* **Enlarge panel** focuses one subplot. **Show all** restores the full figure.
* **F11** enters full screen. **View → Reset three-column layout** restores the default panel widths.

Plot controls wrap in narrow columns. Complex analysis panels remain scrollable. The header shows the project name;
hover over it for the project path.

Help while working
------------------

Open **Help → Tutorial center** with Ctrl+Shift+H, or use the home-page link.
Search tasks, read Steps, Parameters, or Troubleshooting, and use **Open in app** to navigate to the relevant page.
Navigation does not start computation. **A− / A+** controls text size, and **Mark as read** remembers completed reading.
The tutorial is a separate window so you can continue working alongside it.

.. raw:: html

   <a href="../assets/neuroflow-tutorial.png"><img class="product-shot" src="../assets/neuroflow-tutorial.png" alt="Searchable task guide with steps and related page navigation"></a>

**F1** opens the current stage guide. You can disable automatic popups in the guide or Help menu and still open help manually.
The same task text is available in :doc:`task-guide`.

Run and save
------------

Progress counts tasks in the current run: a single task progresses from 0/1 to 1/1.
The right Logs tab records execution. Completed stages save results; use Ctrl+S after changes.
Switching projects or closing the app prompts about unsaved changes. See :doc:`provenance` for output locations.

Shortcuts
---------

.. list-table::
   :header-rows: 1

   * - Keys
     - Action
   * - Ctrl+N / Ctrl+O / Ctrl+S
     - New / open / save project
   * - Ctrl+K
     - Find actions and recent projects
   * - Ctrl+Enter
     - Run selected analysis
   * - Ctrl+B / Ctrl+J
     - Compact left rail / toggle right panel
   * - F1 / Ctrl+Shift+H
     - Stage guide / tutorial center
   * - F11
     - Full screen

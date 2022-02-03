import os.path
import shutil
import sys
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib, Gdk, Gio

app_name = "FI Sort"

class MainWindow(Gtk.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.source_d = None
        self.dest_d = None
        self.queue = []
        self.dones = []
        self.position = 0
        self.goes = []

        self.sc = self.get_style_context()
        self.sm = app.get_style_manager()
        self.css = Gtk.CssProvider.new()
        self.sm.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)
        self.css.load_from_file(Gio.File.new_for_path("style.css"))
        self.sc.add_provider_for_display(self.get_display(), self.css, Gtk.STYLE_PROVIDER_PRIORITY_USER)

        self.set_default_size(1200, 600)
        self.set_title(app_name)


        h = Gtk.HeaderBar()
        self.set_titlebar(h)

        pictures_folder = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_PICTURES)

        b1 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        b2 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        b3 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.toaster = Adw.ToastOverlay()

        b1.append(b2)
        b1.append(Gtk.Separator())
        b1.append(b3)
        self.set_child(self.toaster)
        self.toaster.set_child(b1)

        f = Gtk.Frame()
        f.set_margin_top(5)
        f.set_margin_bottom(3)
        f.set_margin_start(5)
        f.set_margin_end(5)

        p = Gtk.Picture()
        p.set_vexpand(True)
        p.set_hexpand(True)
        self.picture = p
        f.set_child(p)
        b3.append(f)

        self.filename = Gtk.Label()
        b3.append(self.filename)
        self.filename.set_margin_bottom(3)

        b2.set_spacing(5)
        b2.set_margin_start(10)
        b2.set_margin_top(10)
        b2.set_margin_end(10)

        l1 = Gtk.Label(label="Source folder of pictures")
        l1.set_halign(Gtk.Align.START)
        b2.append(l1)
        sfe = Gtk.Entry()
        sfe.set_margin_bottom(5)
        sfe.set_text(pictures_folder)
        self.sfe = sfe

        b2.append(sfe)

        l1 = Gtk.Label(label="Destination folder of folders")
        l1.set_halign(Gtk.Align.START)
        b2.append(l1)
        dfe = Gtk.Entry()
        dfe.set_margin_bottom(10)
        dfe.set_text(pictures_folder)
        self.dfe = dfe
        b2.append(dfe)

        lq = Gtk.Button(label="Load Queue")
        lq.connect("clicked", self.load_queue)
        b2.append(lq)
        lq.grab_focus()

        s = Gtk.Separator()
        s.set_margin_top(15)
        s.set_margin_bottom(15)
        b2.append(s)

        l1 = Gtk.Label(label="Move to folder name")
        #l1.set_halign(Gtk.Align.START)
        b2.append(l1)
        e = Gtk.Entry()
        b2.append(e)
        e.connect("activate", self.go)
        e.set_enable_undo(False)

        info = Gtk.Label(label="Press Load Queue to start")
        info.set_margin_top(30)
        b2.append(info)
        self.info = info

        evk = Gtk.EventControllerKey.new()
        evk.connect("key-pressed", self.search_key_press, e)
        e.add_controller(evk)

        evk = Gtk.EventControllerKey.new()
        evk.connect("key-pressed", self.window_key_press)
        self.add_controller(evk)
        evk.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)

    def window_key_press(self, event, keyval, keycode, state):

        if keyval == Gdk.KEY_Left:
            if self.position > 0:
                self.position -= 1
                self.load_next()
            return True

        if keyval == Gdk.KEY_Right:
            if self.position < len(self.queue) - 1:
                self.position += 1
                self.load_next()
            return True

        if keyval == Gdk.KEY_z and state & Gdk.ModifierType.CONTROL_MASK:
            if not self.dones:
                t = Adw.Toast.new(title=f"No actions to undo")
                self.toaster.add_toast(t)
                return True
            task = self.dones.pop()
            old, new = task
            if type(new) == str:
                if not os.path.isfile(new):
                    t = Adw.Toast.new(title="Error: That file has gone!")
                    self.toaster.add_toast(t)
                    return True
                if os.path.isfile(old):
                    t = Adw.Toast.new(title="Error: Original file exists!")
                    self.toaster.add_toast(t)
                    return True
                shutil.move(new, old)
                t = Adw.Toast.new(title=f"Returned file: {old}")
                self.toaster.add_toast(t)
                self.queue.insert(self.position, os.path.basename(old))
                self.load_next()
            else:
                print(new.get_path())
                t = Adw.Toast.new(title=f"Undo trash not implemented. You'll need to restore the file from trash manually.")
                self.toaster.add_toast(t)
                # self.queue.insert(self.position, os.path.basename(old))
                # self.load_next()

            return True

        if keyval == Gdk.KEY_Delete:
            name, path = self.get_name_path()
            if path:
                f = Gio.File.new_for_path(path)
                self.dones.append((path, f))
                f.trash()
                t = Adw.Toast.new(title=f"Moved file to trash: {os.path.basename(path)}")
                self.toaster.add_toast(t)
                del self.queue[self.position]
                self.load_next()
            return True

    def search_key_press(self, event, keyval, keycode, state, e):

        if keyval == Gdk.KEY_Tab:
            t = e.get_text()
            for item in reversed(self.goes):
                if item.startswith(t):
                    e.set_text(item)
                    e.set_position(len(item))
                    break
            return True

    def get_name_path(self):
        if not self.queue or not -1 < self.position < len(self.queue):
            return None, None
        name = self.queue[self.position]
        path = os.path.join(self.source_d, name)
        return name, path

    def go(self, entry):
        q = entry.get_text()
        item, old = self.get_name_path()
        if not item or not old:
            t = Adw.Toast.new(title="Unexpected Error")
            self.toaster.add_toast(t)
            return

        d = os.path.join(self.dest_d, q)
        if os.path.isfile(d):
            t = Adw.Toast.new(title="Destination folder is a file")
            self.toaster.add_toast(t)
            return
        if not os.path.isdir(d) and os.path.exists(d):
            t = Adw.Toast.new(title="Target error already exists?")
            self.toaster.add_toast(t)
            return
        if not os.path.isdir(d):
            try:
                os.makedirs(d)
                t = Adw.Toast.new(title=f"Created new folder: {q}")
                self.toaster.add_toast(t)
            except:
                t = Adw.Toast.new(title=f"Error making new folder: {q}")
                self.toaster.add_toast(t)
                return

        new = os.path.join(d, item)
        if os.path.exists(new):
            t = Adw.Toast.new(title=f"File {new} already exists!")
            self.toaster.add_toast(t)
            return
        if not os.path.isfile(old):
            t = Adw.Toast.new(title=f"File {old} is gone!")
            self.toaster.add_toast(t)
            return

        try:
            shutil.move(old, new)
            self.dones.append((old, new))
            if q in self.goes:
                del self.goes[self.goes.index(q)]
            self.goes.append(q)
            del self.queue[self.position]
            self.load_next()
            entry.set_text("")
        except:
            t = Adw.Toast.new(title=f"Error moving file!")
            self.toaster.add_toast(t)
            return

    def load_queue(self, button):

        self.source_d = self.sfe.get_text()
        self.dest_d = self.dfe.get_text()
        if not os.path.isdir(self.source_d):
            t = Adw.Toast.new(title="Source directory not found")
            self.toaster.add_toast(t)
            return
        if not os.path.isdir(self.dest_d):
            t = Adw.Toast.new(title="Destination directory not found")
            self.toaster.add_toast(t)
            return

        items = os.listdir(self.source_d)

        # Filter out folders
        for item in items:
            if os.path.isdir(os.path.join(self.source_d, item)):
                if item not in self.goes:
                    self.goes.append(item)
        self.queue = [item for item in items if os.path.isfile(os.path.join(self.source_d, item))]

        self.position = 0
        self.load_next()

    def load_next(self):
        if not self.queue:
            self.picture.set_resource(None)
            self.info.set_text(f"All done")
            return

        item = self.queue[self.position]
        filepath = os.path.join(self.source_d, item)

        self.picture.set_filename(filepath)
        print(f"Load: {filepath}")

        self.info.set_text(f"{self.position + 1} of {len(self.queue)} remaining")
        self.filename.set_text(item)



class MyApp(Adw.Application):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.connect('activate', self.on_activate)

    def on_activate(self, app):
        self.win = MainWindow(application=app)
        self.win.present()


app = MyApp(application_id=f"com.github.taiko2k.{app_name.lower()}")
app.run(sys.argv)

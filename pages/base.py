"""Shared page base: live TabItem ref, body-pane root, defensive select."""
import time


class BasePage:
    def __init__(self, app, tab_control):
        self.app = app
        self.tab = tab_control  # live UIA TabItemControl, never a stored name

    @property
    def name(self) -> str:
        try:
            return self.tab.Name
        except Exception:
            return ""

    @property
    def is_active(self) -> bool:
        try:
            pat = self.tab.GetSelectionItemPattern()
            return bool(pat.IsSelected) if pat else False
        except Exception:
            return False

    @property
    def root(self):
        """Body pane of the active document tab = direct Pane child of doc TabControl."""
        try:
            tf = self.app.doc_tab_folder()
            for c in tf.GetChildren():
                try:
                    if c.ControlTypeName == "PaneControl":
                        return c
                except Exception:
                    continue
        except Exception:
            pass
        return self.app.tab_folder.PaneControl()

    def _descendants(self, control, depth=0, out=None):
        if out is None:
            out = []
        if depth > 10:
            return out
        try:
            for k in control.GetChildren():
                out.append(k)
                self._descendants(k, depth + 1, out)
        except Exception:
            pass
        return out

    def select(self):
        if not self.is_active:
            self.tab.Click()
            time.sleep(0.15)

    def _after_save(self):
        """Hook for pages that must refresh state after saving. Default does nothing."""
        return None

    def save(self):
        """Guarded save for every page: refuses silently-disabled Save with a review error."""
        self.select()
        try:
            available = self.app.save_available()
        except Exception:
            available = False
        if not available:
            raise RuntimeError("Save unavailable (button missing or disabled) - needs review")
        self.app.save()
        return self._after_save()

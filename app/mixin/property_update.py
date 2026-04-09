class PropertyMixin:
    def setPropertyUpddate(self, widget, key, value):
        widget.setProperty(key, value)
        widget.style().unpolish(widget)
        widget.style().polish(widget)
        widget.update()

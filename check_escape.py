import html
print(repr(html.escape('<script>alert(1)</script>')))
print(repr(html.escape('a & b')))
print(repr(html.escape("'quotes'")))
print(repr(html.escape(str(123))))
print(repr(html.escape(str(None))))
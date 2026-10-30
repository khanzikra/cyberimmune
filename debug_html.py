import html
print(repr(html.escape('<script>alert(1)</script>')))
print(repr(html.escape('a & b')))
print(repr(html.escape("'quotes'")))
print(repr(html.escape('EVT-001 <img src=x onerror=alert(1)>')))
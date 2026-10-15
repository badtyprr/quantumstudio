"""Keep every offline-guide topic inside main and paired with a navigation link."""
from html.parser import HTMLParser
from pathlib import Path
class Guide(HTMLParser):
    def __init__(self):
        super().__init__();self.main=False;self.nav=False;self.ids=set();self.sections=[];self.links=[];self.headings=[];self.script=False
    def handle_starttag(self,tag,attributes):
        a=dict(attributes)
        if 'id' in a:
            assert a['id'] not in self.ids,('duplicate id',a['id'])
            self.ids.add(a['id'])
        if tag=='main':self.main=True
        if tag=='nav':self.nav=True
        if tag=='script':self.script=True
        if tag=='section':
            assert self.main and not self.script,'Topic outside searchable main content or after search initialization'
            assert a.get('id') and a.get('aria-labelledby'),a
            self.sections.append(a['id']);self.headings.append(a['aria-labelledby'])
        if tag=='a' and self.nav:self.links.append(a.get('href'))
    def handle_endtag(self,tag):
        if tag=='main':self.main=False
        if tag=='nav':self.nav=False
g=Guide();g.feed((Path(__file__).parent/'Notation-guide.html').read_text(encoding='utf-8'))
assert g.links==['#'+s for s in g.sections],(g.links,g.sections)
assert all(h in g.ids for h in g.headings)
assert len(g.sections)>=44,len(g.sections)
print(f'PASS: all {len(g.sections)} offline-guide topics have searchable content, unique anchors and matching navigation.')

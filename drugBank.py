import scrapy

class BlogSpider(scrapy.Spider):
    name = 'blogspider'
    start_urls = ['https://go.drugbank.com/drugs?approved=1&c=name&d=up&page=1']
    # start_urls = ['https://go.drugbank.com/drugs/DB14099']

    def parse(self, response):
        existing = {}
        for link in response.css("#drugs-table > tbody > tr > td.name-value.text-sm-center.drug-name > strong > a::attr('href')"):
            value = response.follow(link.get(), self.parse_drug)

            yield value

        # for link in response.css("li.page-item.next > a::attr('href')"):
        #     yield response.follow(link.get(), self.parse)

    def innertext_quick(self, elements, delimiter=""):
        try:
            return " ".join(list(delimiter.join(el.strip() for el in element.css('*::text').getall()) for element in elements))
        except:
            return "".join(list(delimiter.join(el.strip() for el in elements.css('*::text').getall())))

    def parse_table(self, response, title, hasPag=False):
        #this is for pagination
        if(hasPag):
            return "table - paginated and paywalled"
        #this is for no pagination
        else:
            table = response.css(f"dl>dt#{title}+dd > table")
            titles = table.css("th")
            titles = [
                self.innertext_quick(field, " ") if 
                self.innertext_quick(field, " ") is not None 
                else field.css("::attr('aria_label')").get()
                for field in titles
            ]
            rows = table.css("tbody > tr > td")
            rows = [row.css("::text").get() for row in rows]
            rows = [rows[i:i+len(titles)] for i in range(0,len(rows),len(titles))]
            x = {}
            for i, title in enumerate(titles):
                x[title] = [rows[x][i] for x in range(0, len(rows))]
            return x

    def parse_field(self, response):
        fin = {}
        for title in response.css('dl>dt[id]'):
            value = None
            #second case: is a list
            if(value is None):
                values = response.css(f"dl>dt#{title.attrib['id']}+dd>ul>li::text").getall()
                if(len(values) > 0):
                    value = values
            #third case: is a list of links
            if(value is None):
                values = response.css(f"dl>dt#{title.attrib['id']}+dd>div>ul>li>a::text").getall()
                if(len(values) > 0):
                    value = values
            #fourth case: is a dl inside of a dd
            if(value is None):
                values = response.css(f"dl>dt#{title.attrib['id']}+dd>dl")
                if(values is not None):
                    values = self.parse_field(values)
                    if(len(values) > 0):
                        value = values
            #fifth case: is an a that is the only child of a dd
            if(value is None):
                value = response.css(f"dl>dt#{title.attrib['id']}+dd>a:only-child::text").get()
            #sixth case: is a bunch of as inside of a dd
            if(value is None):
                spans = response.css(f"dl>dt#{title.attrib['id']}+dd > span")
                found = []
                for span in spans:
                    values = span.css(f"span.separated-list-item>a::text").getall()
                    if(values is not None and len(values) > 0):
                        found += values
                if(len(found) > 0):
                    value = found
            #seventh case: is a bunch of spans inside of a dd
            if(value is None):
                spans = response.css(f"dl>dt#{title.attrib['id']}+dd > span")
                found = []
                for span in spans:
                    values = span.css(f"span.separated-list-item::text").getall()
                    if(values is not None and len(values) > 0):
                        found += values
                if(len(found) > 0):
                    value = found
            #eight case: is a table with pagination
            if(value is None):
                values = response.css(f"dl>dt#{title.attrib['id']}+dd > div[data-gated-content]")
                if(len(values) > 0):
                    value = self.parse_table(response, title.attrib['id'], True)
            #ninth case: is a table without pagination
            if(value is None):
                values = response.css(f"dl>dt#{title.attrib['id']}+dd > table")
                if(len(values) > 0):
                    value = self.parse_table(response, title.attrib['id'])
                    # value = "table_no_pag"
            #tenth case: is structure
            if(value is None):
                if(title.attrib['id'] == "structure"):
                    value = response.css(f"dl>dt#{title.attrib['id']}+dd > div > a::attr('href')").get()
            #last case: some fancy styling stuff, but no actual complex logic
            if(value is None):
                value = self.innertext_quick(response.css(f"dl>dt#{title.attrib['id']}+dd"), " ")
                if(value.startswith("Not Available") or value.endswith("Not Available")):
                    value = None
            fin = {**fin, ** {
                title.attrib['id']: value
            }}
        return fin

    def parse_drug(self, response):
        drug_name = response.css('body > main > div > div.drug-content > div.drug-card > div.content-header.d-sm-flex.align-items-center > h1::text').get()
        fin = {}
        return {drug_name: self.parse_field(response)}
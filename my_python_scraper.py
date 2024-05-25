import requests
from bs4 import BeautifulSoup
import json
from gensim.utils import deaccent

### utility
def unique(list_obj):
    list_obj=list(set(list_obj))
    list_obj.sort()    
    return list_obj


def merge_codes(code):
    # combine them so that espanso can understand
    hex_values = code.split("U+")
    hex_values.pop(0)
    full_code = ""
    for hex in hex_values:
        hex=hex.strip()
        length = len(hex)
        diff = int(8 - length)
        zeros = str("0" * diff)
        full_code += "\\U" + zeros + hex

    return full_code


def build_yaml(names, codes, searches):
    triggers = "\n  - triggers: [\":"
    other_triggers = ":\", \":emoji:\", \";;\"]"
    replace = '\n    replace: "'
    search_terms = "\n    search_terms:"
    pre_search_term = "\n      - \":"
    package_string = "matches:"
    for i in range(len(codes)):
        package_string += (
            triggers + names[i] + other_triggers + replace + codes[i] + '"' + search_terms
        )
        for term in searches[i]:
            package_string += pre_search_term + term + ":\""

    with open("emoji-picker.yaml", "w") as file:
        # Write the string to the file
        file.write(package_string)


def sanitize_name(name):
   return deaccent(name).replace("⊛ ", "").replace(" ", "_").replace("-","_").replace(":","").replace(",","").replace(".","").replace("“","").replace("”","").replace("&","").lower()
     

# main bulk of emoji set
main_emoji_html_filepath = "/mnt/c/Users/Matteo/Downloads/Full Emoji List, v15.1.htm"
mod_emoji_html_filepath = "/mnt/c/Users/Matteo/Downloads/Full Emoji Modifier Sequences, v15.1.htm"

# additional keywords and shortnames
keywords = requests.get(
    "https://raw.githubusercontent.com/muan/emojilib/main/dist/emoji-en-US.json"
)
keywords_dict = json.loads(keywords.text)

# Read the HTML content from the file
with open(main_emoji_html_filepath, "r", encoding="utf-8") as file:
    main_emoji_html_content = file.read()

with open(mod_emoji_html_filepath, "r", encoding="utf-8") as file:
    mod_emoji_html_content = file.read()

# Parse the HTML content of the webpage
main_soup = BeautifulSoup(main_emoji_html_content, "html.parser")
mod_soup = BeautifulSoup(mod_emoji_html_content, "html.parser")

# filter out and build lists from table rows
all_unicodes = []
all_shortcodes = []
all_search_terms = []
category = ""
subcategory = ""

def build_main_emoji_list():
    # get all the table row elements
    table_rows = main_soup.find_all("tr")

    for row in table_rows:
        search_terms = []
        emoji_shortcode = ""
        emoji_keywords = []

        if row.find("th"):
            text = row.get_text(strip=True)
            # check if the row is a category header
            if row.find("th", class_="bighead"):
                category = text.split("&")

            # check if the row is a subcategory header
            if row.find("th", class_="mediumhead"):
                if "-" in text:
                    subcategory = text.split("-")
                if "&" in text:
                    subcategory = text.split("&")

        else:
            # get the current emoji as a string
            emoji = row.find("td", class_="chars").get_text(strip=True)
            emoji_shortcode = sanitize_name(row.find("td", class_="name").get_text(strip=True))

            # handle cases where the emoji string is not in the json list
            if emoji not in keywords_dict:
                # first try searching for the same emoji but with a representation character appended
                emoji = f"{emoji}{chr(65039)}"
                if emoji not in keywords_dict:
                    # if that still doesn't work, ignore the json list and just
                    # set values based on unicode website
                    emoji_keywords = ""

            # else if it can be found continue as usual
            else:
                for keyword in keywords_dict[emoji]:
                    found = False
                    if "_" in keyword:
                        keyword_split = keyword.split("_")
                        found=True
                    if " " in keyword:
                        keyword_split = keyword.split(" ")
                        found=True
                    if "-" in keyword:
                        keyword_split = keyword.split("-")
                        found=True
                    if found:
                        keywords_dict[emoji].pop(keywords_dict[emoji].index(keyword))
                        keywords_dict[emoji].extend(keyword_split)

                emoji_keywords=keywords_dict[emoji]

            all_shortcodes.append(emoji_shortcode)
            all_unicodes.append(merge_codes(row.find("td", class_="code").get_text(strip=True)+"U+FE0F"))

            search_terms.extend(category)
            search_terms.extend(subcategory)
            search_terms.extend(emoji_shortcode.split("_"))
            search_terms.extend(emoji_keywords)
            search_terms = [item.strip().lower() for item in search_terms]
            all_search_terms.append(unique(search_terms))

def build_mod_emoji_list():
    # get all the table row elements
    table_rows = mod_soup.find_all("tr")
    people= ["person", "man", "woman"]

    for row in table_rows:
        #structure of name is base_shortcode: mod, mod...
        base_emoji_shortcode = "" 
        mod_str = ""
        mod_search_terms = []

        if not row.find("th"):
            CLDR_short_name=row.find("td", class_="name").get_text(strip=True)
            CLDR_short_name=CLDR_short_name.replace("medium-light", "mediumxyzzyxlight").replace("medium-dark", "mediumxyzzyxdark")
            base_emoji_shortcode = sanitize_name(CLDR_short_name.split(": ")[0]) # take the left side of the string
            mod_emoji_shortcode = sanitize_name(CLDR_short_name) # full name for the emoji with applied mods

            if len(CLDR_short_name.split(": ")) < 2:    
                # if the length of the keywords is less than 2 than its the plain modifier
                mod_emoji_shortcode=mod_emoji_shortcode.replace("xyzzyx","-")  
                mod_search_terms=mod_emoji_shortcode.split("_")
                mod_emoji_shortcode=mod_emoji_shortcode.replace("xyzzyx","_")  

            else:
                # if there is a base emoji then extract the search terms string
                mod_str = CLDR_short_name.split(": ")[1]
                mod_search_terms = sanitize_name(mod_str).replace("xyzzyx","-").split("_")    
                if mod_search_terms[1] in people:
                    # if the second entry in mod_search_terms is in people, than the emoji is a couple
                    mod_search_terms.append(mod_search_terms[0] + "+" + mod_search_terms[1])

                # search for current emoji
                emoji_index = all_shortcodes.index(base_emoji_shortcode)
                base_emoji_search_terms=all_search_terms[emoji_index].copy()
                base_emoji_search_terms.extend(mod_search_terms)
                mod_search_terms=base_emoji_search_terms
                mod_emoji_shortcode=mod_emoji_shortcode.replace("xyzzyx","_")

            all_shortcodes.append(mod_emoji_shortcode)
            all_unicodes.append(merge_codes(row.find("td", class_="code").get_text(strip=True)+"U+FE0F"))
            all_search_terms.append(unique(mod_search_terms))
                        

build_main_emoji_list()
build_mod_emoji_list()

build_yaml(all_shortcodes, all_unicodes, all_search_terms)
 

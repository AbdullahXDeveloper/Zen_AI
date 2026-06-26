import re

def fix_indentation():
    filepath = 'app/ui/graph_view.py'
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find the wrongly injected methods at the end of the file
    match = re.search(r'(    def _populate_table_and_combos.*)', content, flags=re.DOTALL)
    if not match:
        print("Methods not found!")
        return
        
    methods_code = match.group(1)
    
    # Remove them from their current location
    content = content.replace(methods_code, '')
    
    # Now find where to insert them. We insert them right after `self.web_view.setHtml(error_html)`
    # which is the last line of `_on_graph_error`
    insert_marker = "        self.web_view.setHtml(error_html)\n"
    
    if insert_marker in content:
        content = content.replace(insert_marker, insert_marker + "\n" + methods_code)
        print("Successfully moved methods inside the class.")
    else:
        print("Insert marker not found!")
        
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

fix_indentation()

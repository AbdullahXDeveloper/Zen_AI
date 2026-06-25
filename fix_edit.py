import re

def fix_edit_mode():
    engine_path = 'app/graph/engine.py'
    with open(engine_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Let's replace the whole js_injection script
    js_injection_old = """    <script>
      function configureManipulation(network) {
          network.setOptions({
              manipulation: {
                  enabled: false,
                  addNode: false, // Adding nodes visually is disabled
                  addEdge: function(data, callback) {
                      if (data.from === data.to) {
                          var r = confirm("Do you want to connect the node to itself?");
                          if (!r) return;
                      }
                      var label = prompt("Enter connection label (optional):", "Connected");
                      if (label === null) return; // Cancelled
                      
                      console.log("ZEN_BRIDGE:ADD_EDGE:" + data.from + ":" + data.to + ":" + label);
                      
                      data.label = label;
                      callback(data);
                  },
                  deleteEdge: function(data, callback) {
                      var edgeId = data.edges[0];
                      var edge = network.body.data.edges.get(edgeId);
                      if (edge) {
                          console.log("ZEN_BRIDGE:DEL_EDGE:" + edge.from + ":" + edge.to + ":");
                      }
                      callback(data);
                  },
                  deleteNode: false // Deleting nodes visually is disabled
              }
          });
      }
      
      // Hook into the draw event to ensure the network is initialized
      setTimeout(function() {
          if (typeof network !== "undefined") {
              configureManipulation(network);
          }
      }, 500);
    </script>"""

    # We will use regex to find the script and replace it, because exact string match might fail due to whitespace or previous modifications.
    
    script_regex = r'<script>\s*function configureManipulation\(network\) \{.*?</script>'
    
    js_injection_new = """    <script>
      window.setZenEditMode = function(enable) {
          if (typeof network === "undefined") return;
          network.setOptions({
              manipulation: {
                  enabled: enable,
                  addNode: false,
                  addEdge: function(data, callback) {
                      if (data.from === data.to) {
                          var r = confirm("Do you want to connect the node to itself?");
                          if (!r) return;
                      }
                      var label = prompt("Enter connection label (optional):", "Connected");
                      if (label === null) return;
                      console.log("ZEN_BRIDGE:ADD_EDGE:" + data.from + ":" + data.to + ":" + label);
                      data.label = label;
                      callback(data);
                  },
                  deleteEdge: function(data, callback) {
                      var edgeId = data.edges[0];
                      var edge = network.body.data.edges.get(edgeId);
                      if (edge) {
                          console.log("ZEN_BRIDGE:DEL_EDGE:" + edge.from + ":" + edge.to + ":");
                      }
                      callback(data);
                  },
                  deleteNode: false
              }
          });
      };
      
      setTimeout(function() {
          window.setZenEditMode(false);
      }, 500);
    </script>"""
    
    content = re.sub(script_regex, js_injection_new, content, flags=re.DOTALL)
    
    with open(engine_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("engine.py fixed")


    view_path = 'app/ui/graph_view.py'
    with open(view_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    content = content.replace(
        '''js = "if (typeof network !== 'undefined') { network.setOptions({ manipulation: { enabled: true } }); }"''',
        '''js = "if (typeof window.setZenEditMode === 'function') { window.setZenEditMode(true); }"'''
    )
    content = content.replace(
        '''js = "if (typeof network !== 'undefined') { network.setOptions({ manipulation: { enabled: false } }); }"''',
        '''js = "if (typeof window.setZenEditMode === 'function') { window.setZenEditMode(false); }"'''
    )
    
    with open(view_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("graph_view.py fixed")

fix_edit_mode()

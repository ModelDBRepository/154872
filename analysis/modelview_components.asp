<%@ Language=VBScript %>

<script language="JScript" runat="server" src="./identical/identical_data.js"></script>
<script language="JScript" runat="server" src="./identical/title_db.js"></script>
<script language="JScript" runat="server">


function get_filenames_for_model_id(id) {
    var result, i, key;
    result = [];
    for (key in hash_by_file) {
        i = key.indexOf('/');
        if (key.substr(0, i) == id) {
            result.push(key.substr(i));
        }
    }
    return result;
}

function get_shortname(s) {
    while (s.indexOf('/') >= 0) {
        s = s.substr(s.indexOf('/') + 1);
    }
    return s;
}

function get_modelid(filename) {
    return filename.substr(0, filename.indexOf('/'));
}

function get_matches(id, filename) {
    var hash = hash_by_file[id + filename];
    return files_by_hash[hash];
}

function compute_jsonp(search_id, jsonp_callback) {
    var files;
    files = get_filenames_for_model_id(search_id);


    var duplicates = [];
    var i, j, k, matches, dup, has_entry;
    for (i = 0; i < files.length; i++) {
        matches = get_matches(search_id, files[i]);
        if (matches.length > 1) {
            duplicates.push([files[i], matches]);
        }
    }

    result = jsonp_callback + '({';
    result += '"text": "' + duplicates.length + ' files shared with other ModelDB models"'

    if (duplicates.length > 0) {
        
        // sort in alphabetical order by shortname    
        duplicates.sort(function(a, b) {
            return get_shortname(a[0]) > get_shortname(b[0]);
        });
        
        result += ', "children": ['
        for (j = 0; j < duplicates.length; j++) {
            if (j > 0) {
                result += ', ';
            }
            result += '{"text": "<a href=\\"http://senselab.med.yale.edu/modeldb/ShowModel.asp?model=' + search_id + '&file=' + duplicates[j][0] + '\\">'
            result += get_shortname(duplicates[j][0]);
            result += '</a>"'
            
            result += ', "children": ['
            dup = duplicates[j][1];
            has_entry = false;
            for (k = 0; k < dup.length; k++) {
                // TODO: what if a file is duplicated exactly once in ModelDB, but that duplication is within the same model?
                if (get_modelid(dup[k]) != search_id) {
                    if (has_entry) {
                        result += ', ';
                    }
                    has_entry = true;
                    result += '{"text": "<a href=\\"http://senselab.med.yale.edu/modeldb/ShowModel.asp?model=' + get_modelid(dup[k]) + '&file=/' + dup[k].substr(dup[k].indexOf('/') + 1) + '\\">'
                    // TODO: escape quotes etc in title
                    result += title_db[get_modelid(dup[k])];
                    result += '</a>"'
                    result += ', "noop": true}'
                }                
            }
            result += ']'
            
            result += ', "noop": true}';
        }
        result += ']';
    }

    result += ', "noop": true});';
    return result;
}

</script>
<% =compute_jsonp(Request.Querystring("model"), Request.Querystring("callback")) %>


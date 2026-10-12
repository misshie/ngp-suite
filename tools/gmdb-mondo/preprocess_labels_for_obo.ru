PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX oboInOwl: <http://www.geneontology.org/formats/oboInOwl#>

# Step 1: Relocate multilingual labels to skos:altLabel with explicit lang tag
DELETE {
  ?s rdfs:label ?label_any .
  ?axiom ?p ?o .
}
INSERT {
  # Insert the explicitly tagged string
  ?s skos:altLabel ?tagged_label .
}
WHERE {
  ?s rdfs:label ?label_any .
  FILTER (lang(?label_any) != "en" && lang(?label_any) != "")

  # Embed the language tag directly into the string (e.g., "Label@ja")
  BIND(CONCAT(STR(?label_any), "@", LANG(?label_any)) AS ?tagged_label)

  OPTIONAL {
    ?axiom owl:annotatedSource ?s ;
           owl:annotatedProperty rdfs:label ;
           owl:annotatedTarget ?label_any ;
           ?p ?o .
  }
};

# Step 2: Remove duplicate original labels from obsolete terms
DELETE {
  ?s rdfs:label ?orig_label .
  ?axiom ?p ?o .
}
WHERE {
  ?s owl:deprecated true .
  ?s rdfs:label ?obs_label .
  ?s rdfs:label ?orig_label .
  
  # Keep the label starting with "obsolete " and delete the others
  FILTER (STRSTARTS(LCASE(STR(?obs_label)), "obsolete "))
  FILTER (!STRSTARTS(LCASE(STR(?orig_label)), "obsolete "))

  OPTIONAL {
    ?axiom owl:annotatedSource ?s ;
           owl:annotatedProperty rdfs:label ;
           owl:annotatedTarget ?orig_label ;
           ?p ?o .
  }
};

# Step 3: Resolve any remaining duplicate labels by converting them to exact synonyms (enforce 1 node : 1 label)
DELETE {
  ?s rdfs:label ?extra_label .
  ?axiom ?p ?o .
}
INSERT {
  ?s oboInOwl:hasExactSynonym ?extra_label .
}
WHERE {
  # Find subjects with multiple labels and pick the lexicographically first one to keep
  {
    SELECT ?s (MIN(STR(?l)) AS ?keep_str)
    WHERE {
      ?s rdfs:label ?l .
    }
    GROUP BY ?s
    HAVING (COUNT(?l) > 1)
  }
  
  # Target the remaining labels for removal/conversion
  ?s rdfs:label ?extra_label .
  FILTER (STR(?extra_label) != ?keep_str)

  OPTIONAL {
    ?axiom owl:annotatedSource ?s ;
           owl:annotatedProperty rdfs:label ;
           owl:annotatedTarget ?extra_label ;
           ?p ?o .
  }
}


from typing import Dict, Any, List, Tuple

def _parse_composite_omim(omim_value: Any) -> Tuple[int | None, str | None]:
    """
    Parses a composite OMIM string (e.g., "600123, PS123456") into its parts.
    """
    if not omim_value:
        return None, None
    
    parts = [p.strip() for p in str(omim_value).split(',')]
    numeric_id_str = next((p for p in parts if not p.startswith('PS')), None)
    ps_id = next((p for p in parts if p.startswith('PS')), None)
    
    numeric_id = int(numeric_id_str) if numeric_id_str and numeric_id_str.isdigit() else None
    
    return numeric_id, ps_id

def _rank_key(entry: Dict[str, Any]) -> float:
    rank = entry.get('pubcasefinder_rank')
    return rank if isinstance(rank, (int, float)) else float('inf')

def _add_gm_rank_and_score(item_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not item_list: return []
    for i, item in enumerate(item_list): item['gm_rank'] = i + 1
    try:
        distances = [item['distance'] for item in item_list]
        min_dist, max_dist = min(distances), max(distances)
        dist_range = max_dist - min_dist
        if dist_range == 0:
            for item in item_list: item['score'] = 1.0
        else:
            for item in item_list: item['score'] = 1.0 - (item['distance'] - min_dist) / dist_range
    except (KeyError, ValueError):
        for item in item_list: item['score'] = None
    return item_list

def _add_meta_rank_to_list(item_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not item_list: return []
    for item in item_list:
        gm_rank = item.get('gm_rank')
        pcf_rank = item.get('pubcasefinder_rank')
        item['mean_rank'] = (gm_rank + pcf_rank) / 2 if isinstance(gm_rank, (int, float)) and isinstance(pcf_rank, (int, float)) else None
    item_list.sort(key=lambda x: (x.get('mean_rank') is None, x.get('mean_rank')))
    for i, item in enumerate(item_list): item['meta_rank'] = i + 1
    return item_list

def integrate_json(raw_results: Dict[str, Any]) -> Dict[str, Any]:
    print("--- Starting results integration ---")

    # Step 1: Pre-process raw GestaltMatcher lists
    for key in ['suggested_syndromes_list', 'suggested_genes_list', 'suggested_patients_list']:
        if key in raw_results:
            raw_results[key] = _add_gm_rank_and_score(raw_results[key])
    
    patient_key = 'suggested_patients_list'
    if patient_key in raw_results:
        for patient in raw_results[patient_key]:
            numeric_omim, ps_id = _parse_composite_omim(patient.get('omim_id'))
            patient['numeric_omim_id'] = numeric_omim
            patient['phenotypic_series_id'] = ps_id
            patient['omim_id_for_match'] = numeric_omim

    # Step 2: Enrich with PubCaseFinder data
    pcf_data = raw_results.get('pubcasefinder')
    
    if pcf_data and isinstance(pcf_data, dict) and 'ranked_list' in pcf_data:
        pcf_results_list = pcf_data.get('ranked_list', [])
        
        pcf_by_omim = {}
        pcf_by_mondo = {}
        pcf_by_gene = {}
        for item in pcf_results_list:
            entry = {'pubcasefinder_rank': item.get('rank'), 'pubcasefinder_score': item.get('score')}
            if item.get('id') and item['id'].startswith('OMIM:'):
                omim_id_str = item['id'].replace('OMIM:', '')
                pcf_by_omim[omim_id_str] = entry
            # The OMIM-targeted response already carries MONDO IDs, so no extra request
            # is needed. Several OMIM entries can share a MONDO term; keep the best rank.
            for mondo_id in (item.get('mondo_id') or []):
                previous = pcf_by_mondo.get(mondo_id)
                if previous is None or _rank_key(entry) < _rank_key(previous):
                    pcf_by_mondo[mondo_id] = entry
            if item.get('hgnc_gene_symbol') and isinstance(item.get('hgnc_gene_symbol'), list):
                for gene_symbol in item['hgnc_gene_symbol']:
                    pcf_by_gene[gene_symbol] = entry
        
        if 'suggested_syndromes_list' in raw_results:
            for item in raw_results['suggested_syndromes_list']:
                mondo_id = item.get('mondo_id')
                omim_id = item.get('omim_id')
                if mondo_id and mondo_id in pcf_by_mondo:
                    item.update(pcf_by_mondo[mondo_id])
                elif omim_id and str(omim_id) in pcf_by_omim:
                    # Rows MONDO could not place still match through their GMDB OMIM ID.
                    item.update(pcf_by_omim[str(omim_id)])

        if patient_key in raw_results:
            for item in raw_results[patient_key]:
                omim_id = item.get('omim_id_for_match')
                if omim_id and str(omim_id) in pcf_by_omim:
                    item.update(pcf_by_omim[str(omim_id)])

        if 'suggested_genes_list' in raw_results:
            for item in raw_results['suggested_genes_list']:
                gene_name = item.get('gene_name')
                if gene_name and gene_name in pcf_by_gene:
                    item.update(pcf_by_gene[gene_name])

    # Step 3: Apply meta-ranking
    for key in ['suggested_syndromes_list', 'suggested_genes_list', 'suggested_patients_list']:
         if key in raw_results:
            raw_results[key] = _add_meta_rank_to_list(raw_results[key])

    print("--- Integration and meta-ranking complete ---")
    return raw_results


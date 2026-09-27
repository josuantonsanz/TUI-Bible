
# Morphology dictionaries provided by user

dicTipoPalabra = {
    "V": "v",         # Verbo
    "A": "adj",       # Adjetivo
    "K": "pron.cor",  # Pronombre correlativo
    "C": "pron.rec",  # Pronombre recícproco
    "I": "pron.int",  # Pronombre interrogativo
    "F": "pron.refl", # Pronombre reflexivo
    "Q": "pron", # Pronombre correlativo o interrogativo
    "X": "pron.ind", # Pronombre indefinido
    "T": "art",  # Artículo definido
    "R": "pron.rel", # Pronombre relativo
    "S": "pron.pos", # Pronombre posesivo
    "D": "pron.dem", # Pronombre demostrativo
    "P": "pron.pers", # Pronombre personal
    "N": "sust", # Sustantivo
    "COND": "cond", # Condicional
    "CONJ": "conj", # Conjunción
    "INJ": "interj", # Interjección
    "PREP": "prep", # Preposición
    "ADV": "adv", # Adverbio
    "ARAM": "aram", # Trasliteración aramea indeclinable
    "HEB": "heb", # Transliteración hebrea indeclinable
    "NUI": "num.ind", # Numeral indeclinable
    "PRT": "part", # Partícula
}

dicTipoPart = {
    "I": "int", # Interrogativa
    "N": "neg", # Negativa
}

dicTipoCaso = {
    "N": "nom", # Nominativo
    "V": "voc", # Vocativo
    "A": "acu", # Acusativo
    "G": "gen", # Genitivo
    "B": "abl", # Ablativo
    "D": "dat"  # Dativo
}

dicTipoGen = {
    "M": "m", # Masculino
    "F": "f", # Femenino
    "N": "n"  # Neutro
}

dicTipoNum = {"S": "s", "P": "p"} # Singular y plural

dicTipoTiempo = {
    "P": "pres",     # Presente
    "2P": "2pres",   # Presente 2do
    "F": "fut",      # Futuro
    "2F": "2fut",    # Futuro 2do
    "I": "imp",      # Imperfecto
    "R": "perf",     # Perfecto
    "2R": "2perf",   # Perfecto 2do
    "A": "aor",      # Aoristo
    "2A": "2aor",    # Aoristo 2do
    "L": "pluspf",   # Pluscuamperfecto
    "2L": "2pluspf", # Pluscuamperfecto 2do
    "X": "-",        # Sin tiempo
    
}

dicTipoVoz = {
    "A": "act",     # Activo
    "M": "med",     # Medio
    "P": "pas",     # Pasivo
    "E": "mp",      # Medio o pasivo
    "D": "dep.med", # Deponente medio
    "N": "dep.mp", # Deponente pasivo
    "O": "dep.pas", # Deponente Pasivo
    "X": "-",       # Sin voz
}

dicTipoModo = {
    "I": "ind",  # Indicativo
    "S": "sub",  # Subjuntivo
    "P": "part", # Participio
    "N": "inf",  # Infinitivo
    "M": "imp",  # Imperativo
    "O": "opt",  # Optativo
    
}

def expand_morphology(code: str) -> str:
    """
    Expands a Robinson Morphological Analysis Code (RMAC) into a human-readable string
    using the provided dictionaries.
    
    Format example: N-GSM -> Sustantivo, genitivo singular masculino
    """
    if not code:
        return ""
        
    parts = code.split('-')
    if not parts:
        return code
        
    pos_code = parts[0]
    details = parts[1] if len(parts) > 1 else ""
    
    # 1. Part of Speech
    pos_desc = dicTipoPalabra.get(pos_code, pos_code)
    
    result_parts = [pos_desc]
    
    # Handle specifics based on POS
    # N (Noun), A (Adjective), T (Article), P/R/D... (Pronouns) usually have Case, Number, Gender
    # V (Verb) has Tense, Voice, Mood, (Person, Number) or (Case, Number, Gender if Participle)
    
    if pos_code in ["N", "A", "T", "S", "D", "R", "P", "K", "I", "X", "Q", "F"]:
        # Standard Noun-like pattern: Case, Number, Gender
        # e.g. GSM -> Genitive Singular Masculine
        if len(details) >= 3:
            case_c = details[0]
            num_c = details[1]
            gen_c = details[2]
            
            result_parts.append(dicTipoCaso.get(case_c, case_c))
            result_parts.append(dicTipoNum.get(num_c, num_c))
            result_parts.append(dicTipoGen.get(gen_c, gen_c))
            
    elif pos_code == "V":
        # Verbs: Tense, Voice, Mood
        # e.g. PAI-3S -> Present Active Indicative, 3rd Person Singular
        # e.g. PAP-NSM -> Present Active Participle, Nominative Singular Masculine
        if len(details) >= 3:
            tense_c = details[0:1] # Could be 2 chars if starts with 2? No, map keys are P, 2P...
            # The dictionary has 2-char keys '2P', '2F' etc. 
            # We need to peek if the second char makes it a 2-char key.
            # Usually strict positions? RMAC: Tense(1), Voice(1), Mood(1)
            # Exception: Tense can be '2P'.
            
            # Let's check against keys.
            idx = 0
            # Try 2 chars
            if len(details) > 1 and details[0:2] in dicTipoTiempo:
                tense_key = details[0:2]
                idx = 2
            else:
                tense_key = details[0]
                idx = 1
                
            voice_key = details[idx] if idx < len(details) else ""
            idx += 1
            mood_key = details[idx] if idx < len(details) else ""
            idx += 1
            
            result_parts.append(dicTipoTiempo.get(tense_key, tense_key))
            result_parts.append(dicTipoVoz.get(voice_key, voice_key))
            result_parts.append(dicTipoModo.get(mood_key, mood_key))
            
            # Remaining: Person/Num or Case/Num/Gen
            remaining = details[idx:]
            if remaining.startswith("-"): remaining = remaining[1:] # should not happen as split by -
            
            # Actually, the remainder is usually part of the same block in RMAC if no dash?
            # Standard RMAC: V-PAI-3S. split('-') -> ['V', 'PAI', '3S']
            # My logic split only first dash? code.split('-') defaults to all.
            # If code is V-PAI-3S
            # parts = ['V', 'PAI', '3S']
            # details (var) was just parts[1] above. I need to handle multipart.
            pass

    # Refined Logic for parsing
    # The split behavior above was simplistic. Let's redo extracting parts.
    
    parts = code.split('-')
    pos_code = parts[0]
    
    # Reset result
    pos_text = dicTipoPalabra.get(pos_code, pos_code)
    descriptors = []
    
    if pos_code == "V":
        # Verb
        if len(parts) > 1:
            tvm = parts[1] # Tense Voice Mood
            
            # Consume Tense
            if len(tvm) > 1 and tvm[0:2] in dicTipoTiempo:
                descriptors.append(dicTipoTiempo.get(tvm[0:2]))
                vm = tvm[2:]
            elif len(tvm) > 0:
                descriptors.append(dicTipoTiempo.get(tvm[0], tvm[0]))
                vm = tvm[1:]
            else:
                vm = ""
                
            # Consume Voice
            if len(vm) > 0:
                descriptors.append(dicTipoVoz.get(vm[0], vm[0]))
                m = vm[1:]
            else:
                m = ""
                
            # Consume Mood
            if len(m) > 0:
                descriptors.append(dicTipoModo.get(m[0], m[0]))
                
        if len(parts) > 2:
            suffix = parts[2]
            # If Mood was Participle (P), suffix is CaseNumGen (e.g. NSM)
            # If Mood was Indicative/Subj/Opt/Imp, suffix is PersonNum (e.g. 3S)
            # Warning: Mood is determined above.
            
            # Check if suffix looks like Case (N,V,A,G,D)
            if suffix and suffix[0] in dicTipoCaso:
                 # Participial suffix: Case, Num, Gen
                 if len(suffix) >= 3:
                     descriptors.append(dicTipoCaso.get(suffix[0], suffix[0]))
                     descriptors.append(dicTipoNum.get(suffix[1], suffix[1]))
                     descriptors.append(dicTipoGen.get(suffix[2], suffix[2]))
            # Else Person Number (1S, 2P etc)
            elif len(suffix) >= 2 and suffix[0].isdigit():
                person = suffix[0]
                num = suffix[1]
                descriptors.append(f"{person}ª pers") # 1st -> 1ª pers
                descriptors.append(dicTipoNum.get(num, num))
                
    elif pos_code in ["N", "A", "T", "S", "D", "R", "P", "K", "I", "X", "Q", "F"]:
        # Nouns/Adjectives etc.
        # Format: N-GSM
        if len(parts) > 1:
            cng = parts[1]
            if len(cng) >= 3:
                descriptors.append(dicTipoCaso.get(cng[0], cng[0]))
                descriptors.append(dicTipoNum.get(cng[1], cng[1]))
                descriptors.append(dicTipoGen.get(cng[2], cng[2]))
    
    elif pos_code == "PRT":
         if len(parts) > 1:
             pt = parts[1]
             descriptors.append(dicTipoPart.get(pt, pt))

    # Join non-None descriptors
    final_desc = ", ".join([d for d in descriptors if d])
    
    if final_desc:
        return f"{pos_text}, {final_desc}"
    else:
        return pos_text


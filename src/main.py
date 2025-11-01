import NXOpen
import csv
import os
from collections import Counter

def get_component_partname(comp):
    """
    Versucht, einen stabilen Partnamen für eine Component zu bekommen.
    Rückgabe: string oder None
    """
    try:
        proto = comp.Prototype
    except:
        proto = None

    if proto is None:
        return None

    # 1) Versuch: OwningPart (zuverlässigster Weg zum eigentlichen NX-Part)
    try:
        owning_part = proto.OwningPart
    except:
        owning_part = None

    if owning_part is not None:
        # bevorzugt eine "Nummer" ohne Pfad
        for attr in [owning_part.Leaf, owning_part.Name]:
            try:
                if attr and attr.strip():
                    return attr.strip()
            except:
                pass

        # notfalls kompletter Pfad -> Dateiname extrahieren
        try:
            fullpath = owning_part.FullPath
            if fullpath and fullpath.strip():
                base = os.path.basename(fullpath)
                name_no_ext = os.path.splitext(base)[0]
                if name_no_ext.strip():
                    return name_no_ext.strip()
        except:
            pass

    # 2) Fallback: Prototype.DisplayName (manchmal gefüllt)
    try:
        disp = proto.DisplayName
        if disp and disp.strip():
            base = os.path.basename(disp)
            return os.path.splitext(base)[0].strip()
    except:
        pass

    # 3) letzter Fallback: Instanzname in der Baugruppe
    try:
        nm = comp.Name
        if nm and nm.strip():
            return nm.strip()
    except:
        pass

    return None


def walk_components(component, parts_list):
    """
    Rekursiv durch alle Kinder laufen.
    Für jedes Child einen Partnamen ermitteln und in parts_list anhängen.
    """
    # Kinder holen
    try:
        children = component.GetChildren()
    except:
        children = []

    for child in children:
        # Partnamen vom Child ermitteln
        partname = get_component_partname(child)
        if partname is not None:
            parts_list.append(partname)

        # und rekursiv tiefer
        walk_components(child, parts_list)


def main():
    session = NXOpen.Session.GetSession()
    work_part = session.Parts.Work

    if work_part is None:
        raise Exception("Kein aktives Work Part gefunden.")

    root = work_part.ComponentAssembly.RootComponent
    if root is None:
        raise Exception("Das aktive Part ist keine Baugruppe (hat keinen RootComponent).")

    # Liste aller (Sub-)Parts sammeln.
    # WICHTIG: wir starten jetzt BEI DEN KINDERN der Root,
    # damit die Root-Baugruppe selbst nicht gezählt wird.
    parts_list = []
    walk_components(root, parts_list)

    # Zählen
    counts = Counter(parts_list)

    # CSV schreiben
    out_path = os.path.join(os.path.expanduser("~"), "bom_compact.csv")
    with open(out_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(["PartName", "Count"])
        # sortiert nach PartName
        for part_name in sorted(counts.keys()):
            writer.writerow([part_name, counts[part_name]])

    # Rückmeldung im NX Listing Window
    lw = session.ListingWindow
    if not lw.IsOpen:
        lw.Open()

    lw.WriteLine("Stückliste exportiert nach: " + out_path)
    lw.WriteLine("Unterschiedliche Parts (ohne Root): " + str(len(counts)))
    lw.WriteLine("Gesamtinstanzen aller Parts: " + str(sum(counts.values())))

if __name__ == "__main__":
    main()

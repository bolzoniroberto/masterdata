#!/usr/bin/env python3
"""
Script diagnostico per verificare dati organigrammi
Controlla se i campi gerarchici sono stati popolati correttamente
"""

import sqlite3
from pathlib import Path
import sys

def verify_hierarchy_data():
    """Verifica dati gerarchie nei 3 organigrammi"""

    db_path = Path('data/db/app.db')

    if not db_path.exists():
        print("❌ Database non trovato:", db_path)
        return False

    print(f"🔍 Verifica dati organigrammi in: {db_path}\n")
    print("="*70)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1. Verifica esistenza colonne
    print("\n📋 STEP 1: Verifica schema database")
    print("-"*70)

    cursor.execute("PRAGMA table_info(employees)")
    employee_columns = {col[1] for col in cursor.fetchall()}

    required_employee_cols = ['reports_to_cf', 'cod_tns', 'padre_tns']
    for col in required_employee_cols:
        status = '✅' if col in employee_columns else '❌'
        print(f"  {status} employees.{col}")

    cursor.execute("PRAGMA table_info(org_units)")
    orgunit_columns = {col[1] for col in cursor.fetchall()}

    status = '✅' if 'parent_org_unit_id' in orgunit_columns else '❌'
    print(f"  {status} org_units.parent_org_unit_id")

    # 2. Verifica dati popolati
    print("\n📊 STEP 2: Verifica dati popolati")
    print("-"*70)

    # Total employees
    cursor.execute("SELECT COUNT(*) FROM employees")
    total_employees = cursor.fetchone()[0]
    print(f"\n  Totale dipendenti: {total_employees}")

    # HR Hierarchy (reports_to_cf)
    cursor.execute("""
        SELECT COUNT(*)
        FROM employees
        WHERE reports_to_cf IS NOT NULL
        AND reports_to_cf != ''
    """)
    hr_count = cursor.fetchone()[0]
    hr_pct = (hr_count / total_employees * 100) if total_employees > 0 else 0
    print(f"\n  🌳 ORGANIGRAMMA HR:")
    print(f"     Dipendenti con responsabile diretto: {hr_count}/{total_employees} ({hr_pct:.1f}%)")

    if hr_count > 0:
        # Mostra sample
        cursor.execute("""
            SELECT titolare, tx_cod_fiscale, reports_to_cf
            FROM employees
            WHERE reports_to_cf IS NOT NULL AND reports_to_cf != ''
            LIMIT 3
        """)
        print(f"     Esempi:")
        for row in cursor.fetchall():
            print(f"       • {row[0]} (CF: {row[1]}) → Resp: {row[2]}")
    else:
        print(f"     ⚠️  NESSUN DATO - Colonna CZ non mappata o vuota!")

    # TNS Hierarchy (cod_tns + padre_tns)
    cursor.execute("""
        SELECT COUNT(*)
        FROM employees
        WHERE cod_tns IS NOT NULL
        AND cod_tns != ''
    """)
    tns_count = cursor.fetchone()[0]
    tns_pct = (tns_count / total_employees * 100) if total_employees > 0 else 0
    print(f"\n  🌳 ORGANIGRAMMA TNS:")
    print(f"     Dipendenti con codice TNS: {tns_count}/{total_employees} ({tns_pct:.1f}%)")

    if tns_count > 0:
        cursor.execute("""
            SELECT COUNT(*)
            FROM employees
            WHERE padre_tns IS NOT NULL
            AND padre_tns != ''
        """)
        padre_count = cursor.fetchone()[0]
        print(f"     Dipendenti con padre TNS: {padre_count}/{tns_count} ({padre_count/tns_count*100:.1f}%)")

        # Mostra sample
        cursor.execute("""
            SELECT titolare, cod_tns, padre_tns
            FROM employees
            WHERE cod_tns IS NOT NULL AND cod_tns != ''
            LIMIT 3
        """)
        print(f"     Esempi:")
        for row in cursor.fetchall():
            padre = row[2] if row[2] else '(root)'
            print(f"       • {row[0]} - TNS: {row[1]} → Padre: {padre}")
    else:
        print(f"     ⚠️  NESSUN DATO - Colonne CB/CC non mappate o vuote!")

    # ORG Hierarchy (org_units + parent_org_unit_id)
    cursor.execute("SELECT COUNT(*) FROM org_units")
    total_org_units = cursor.fetchone()[0]
    print(f"\n  🌳 ORGANIGRAMMA ORG:")
    print(f"     Totale posizioni organizzative: {total_org_units}")

    if total_org_units > 0:
        cursor.execute("""
            SELECT COUNT(*)
            FROM org_units
            WHERE parent_org_unit_id IS NOT NULL
        """)
        org_with_parent = cursor.fetchone()[0]
        org_pct = (org_with_parent / total_org_units * 100) if total_org_units > 0 else 0
        print(f"     Posizioni con parent: {org_with_parent}/{total_org_units} ({org_pct:.1f}%)")

        # Mostra sample
        cursor.execute("""
            SELECT o.codice, o.descrizione, parent.codice as parent_code
            FROM org_units o
            LEFT JOIN org_units parent ON o.parent_org_unit_id = parent.org_unit_id
            WHERE o.parent_org_unit_id IS NOT NULL
            LIMIT 3
        """)
        print(f"     Esempi:")
        for row in cursor.fetchall():
            print(f"       • {row[0]} ({row[1]}) → Parent: {row[2]}")
    else:
        print(f"     ⚠️  NESSUNA POSIZIONE ORGANIZZATIVA!")

    # 3. Verifica integrità referenziale
    print("\n🔗 STEP 3: Verifica integrità referenziale")
    print("-"*70)

    # HR: Controlla CF responsabili che non esistono come dipendenti
    cursor.execute("""
        SELECT DISTINCT e.reports_to_cf
        FROM employees e
        WHERE e.reports_to_cf IS NOT NULL
        AND e.reports_to_cf != ''
        AND NOT EXISTS (
            SELECT 1 FROM employees e2
            WHERE e2.tx_cod_fiscale = e.reports_to_cf
        )
    """)
    orphan_hr = cursor.fetchall()
    if orphan_hr:
        print(f"\n  ⚠️  HR: {len(orphan_hr)} CF responsabili non trovati come dipendenti")
        print(f"     Primi 3: {[row[0] for row in orphan_hr[:3]]}")
    else:
        print(f"  ✅ HR: Tutti i CF responsabili sono dipendenti esistenti")

    # TNS: Controlla codici padre TNS che non esistono
    cursor.execute("""
        SELECT DISTINCT e.padre_tns
        FROM employees e
        WHERE e.padre_tns IS NOT NULL
        AND e.padre_tns != ''
        AND NOT EXISTS (
            SELECT 1 FROM employees e2
            WHERE e2.cod_tns = e.padre_tns
        )
    """)
    orphan_tns = cursor.fetchall()
    if orphan_tns:
        print(f"\n  ⚠️  TNS: {len(orphan_tns)} codici padre TNS non trovati")
        print(f"     Primi 3: {[row[0] for row in orphan_tns[:3]]}")
    else:
        print(f"  ✅ TNS: Tutti i padre TNS sono codici esistenti")

    # 4. Verifica mapping salvato
    print("\n💾 STEP 4: Verifica mapping colonne salvato")
    print("-"*70)

    mapping_file = Path('config/column_mapping.json')
    if mapping_file.exists():
        import json
        with open(mapping_file) as f:
            mapping = json.load(f)

        print(f"\n  ✅ File mapping trovato: {mapping_file}")
        print(f"\n  Mappature colonne gerarchie:")

        hierarchy_mappings = {
            'CF Responsabile Diretto': mapping.get('CF Responsabile Diretto'),
            'Codice TNS': mapping.get('Codice TNS'),
            'Padre TNS': mapping.get('Padre TNS'),
            'ReportsTo': mapping.get('ReportsTo')
        }

        for sys_col, excel_col in hierarchy_mappings.items():
            if excel_col:
                print(f"     • {sys_col:25} → {excel_col}")
            else:
                print(f"     ⚠️  {sys_col:25} → NON MAPPATO!")
    else:
        print(f"  ⚠️  File mapping non trovato: {mapping_file}")
        print(f"     Il mapping non è stato salvato durante l'import!")

    # 5. Diagnosi e raccomandazioni
    print("\n\n🎯 DIAGNOSI E RACCOMANDAZIONI")
    print("="*70)

    issues = []

    if hr_count == 0:
        issues.append({
            'organigramma': 'HR',
            'problema': 'Nessun dipendente ha reports_to_cf popolato',
            'causa': 'Colonna CZ non mappata o vuota nel file Excel',
            'soluzione': 'Rifai import e assicurati di mappare "CF Responsabile Diretto" alla colonna CZ'
        })

    if tns_count == 0:
        issues.append({
            'organigramma': 'TNS',
            'problema': 'Nessun dipendente ha cod_tns popolato',
            'causa': 'Colonne CB/CC non mappate o vuote nel file Excel',
            'soluzione': 'Rifai import e assicurati di mappare "Codice TNS" (CB) e "Padre TNS" (CC)'
        })

    if org_with_parent == 0 and total_org_units > 0:
        issues.append({
            'organigramma': 'ORG',
            'problema': 'Nessuna posizione ha parent_org_unit_id popolato',
            'causa': 'Colonna AC (ReportsTo) non mappata o vuota nel file Excel',
            'soluzione': 'Rifai import e assicurati di mappare "ReportsTo" alla colonna AC'
        })

    if issues:
        print("\n❌ PROBLEMI TROVATI:\n")
        for i, issue in enumerate(issues, 1):
            print(f"{i}. ORGANIGRAMMA {issue['organigramma']}:")
            print(f"   Problema: {issue['problema']}")
            print(f"   Causa: {issue['causa']}")
            print(f"   Soluzione: {issue['soluzione']}\n")

        print("\n📋 AZIONI DA FARE:")
        print("   1. Vai al tab 'Gestione Dati' → 'Nuovo Import'")
        print("   2. Carica il file Excel DB_ORG")
        print("   3. Nello Step 2 - Mapping Colonne:")
        print("      • Verifica che 'CF Responsabile Diretto' sia mappato alla colonna CZ")
        print("      • Verifica che 'Codice TNS' sia mappato alla colonna CB")
        print("      • Verifica che 'Padre TNS' sia mappato alla colonna CC")
        print("      • Verifica che 'ReportsTo' sia mappato alla colonna AC")
        print("   4. Completa l'import")
        print("   5. Riesegui questo script per verificare")
    else:
        print("\n✅ TUTTO OK! I dati sono popolati correttamente.")
        print("   Gli organigrammi dovrebbero visualizzarsi.")
        print("\n   Se gli organigrammi non si vedono ancora, il problema potrebbe essere:")
        print("   • Le view UI non chiamano i metodi corretti del servizio")
        print("   • I componenti organigramma non renderizzano i dati")
        print("\n   Prossimo step: Verifica i log dell'app quando apri gli organigrammi")

    conn.close()
    return len(issues) == 0

if __name__ == '__main__':
    try:
        success = verify_hierarchy_data()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ ERRORE durante verifica: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

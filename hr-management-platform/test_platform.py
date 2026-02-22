"""
Test rapido funzionalità core della piattaforma
"""
import sys
from pathlib import Path

# Setup path
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

import config
from services.excel_handler import ExcelHandler
from services.validator import DataValidator
from services.merger import DBTNSMerger

def test_load_data():
    """Test caricamento dati"""
    print("=" * 80)
    print("TEST 1: Caricamento dati")
    print("=" * 80)
    
    handler = ExcelHandler()
    personale, strutture, db_tns = handler.load_data()
    
    print(f"✅ Personale caricato: {len(personale)} record")
    print(f"✅ Strutture caricate: {len(strutture)} record")
    if db_tns is not None:
        print(f"✅ DB_TNS esistente: {len(db_tns)} record")
    else:
        print("ℹ️  DB_TNS non presente (verrà generato)")
    
    return handler, personale, strutture, db_tns


def test_validation(personale, strutture):
    """Test validazione"""
    print("\n" + "=" * 80)
    print("TEST 2: Validazione dati")
    print("=" * 80)
    
    # Valida Personale
    print("\n📋 Validazione TNS Personale...")
    result_pers = DataValidator.validate_personale(personale)
    print(f"  {result_pers.get_summary()}")
    
    if result_pers.errors:
        print(f"  ❌ Errori trovati: {len(result_pers.errors)}")
        for err in result_pers.errors[:3]:
            print(f"    - Row {err['row']}, {err['field']}: {err['message']}")
    
    # Valida Strutture
    print("\n🏗️  Validazione TNS Strutture...")
    result_strut = DataValidator.validate_strutture(strutture)
    print(f"  {result_strut.get_summary()}")
    
    if result_strut.errors:
        print(f"  ❌ Errori trovati: {len(result_strut.errors)}")
        for err in result_strut.errors[:3]:
            print(f"    - Row {err['row']}, {err['field']}: {err['message']}")
    
    # Record incompleti
    print("\n🔍 Ricerca anomalie...")
    incomplete_pers = DataValidator.find_incomplete_records_personale(personale)
    incomplete_strut = DataValidator.find_incomplete_records_strutture(strutture)
    orphans = DataValidator.find_orphan_structures(strutture, personale)
    
    print(f"  - Record incompleti Personale: {len(incomplete_pers)}")
    print(f"  - Record incompleti Strutture: {len(incomplete_strut)}")
    print(f"  - Strutture orfane: {len(orphans)}")
    
    # Duplicati
    has_dup_pers, dup_pers = DataValidator.check_duplicate_keys(personale, 'TxCodFiscale')
    has_dup_strut, dup_strut = DataValidator.check_duplicate_keys(strutture, 'Codice')
    
    print(f"  - CF duplicati: {len(dup_pers) if has_dup_pers else 0}")
    print(f"  - Codici duplicati Strutture: {len(dup_strut) if has_dup_strut else 0}")


def test_merge(personale, strutture):
    """Test generazione DB_TNS"""
    print("\n" + "=" * 80)
    print("TEST 3: Generazione DB_TNS")
    print("=" * 80)
    
    # Merge
    db_tns, warnings = DBTNSMerger.merge_data(personale, strutture)
    
    print(f"✅ DB_TNS generato: {len(db_tns)} record")
    
    if warnings:
        print(f"\n⚠️  Warning ({len(warnings)}):")
        for warn in warnings[:5]:
            print(f"  - {warn}")
    
    # Validazione
    is_valid, errors = DBTNSMerger.validate_db_tns(db_tns)
    
    if is_valid:
        print("\n✅ DB_TNS valido!")
    else:
        print(f"\n❌ DB_TNS con errori ({len(errors)}):")
        for err in errors:
            print(f"  - {err}")
    
    # Statistiche
    stats = DBTNSMerger.get_statistics(db_tns)
    
    print("\n📊 Statistiche DB_TNS:")
    print(f"  - Totale record: {stats['total_records']}")
    print(f"  - Strutture: {stats['strutture_count']}")
    print(f"  - Personale: {stats['personale_count']}")
    print(f"  - Codici univoci: {stats['unique_codes']}")
    print(f"  - Codici duplicati: {stats['duplicate_codes']}")
    print(f"  - Strutture root: {stats['root_structures']}")
    
    return db_tns


def test_save(handler, personale, strutture, db_tns):
    """Test salvataggio"""
    print("\n" + "=" * 80)
    print("TEST 4: Salvataggio & Export")
    print("=" * 80)
    
    # Export in output
    output_path = handler.export_to_output(
        personale,
        strutture,
        db_tns,
        prefix="TEST_Export"
    )
    
    print(f"✅ File esportato: {output_path}")
    print(f"  Dimensione: {output_path.stat().st_size / 1024:.2f} KB")
    
    # Lista backup
    backups = handler.get_backup_list()
    print(f"\n📦 Backup disponibili: {len(backups)}")
    if backups:
        print(f"  Ultimo backup: {backups[0]['name']}")


def main():
    """Esegue tutti i test"""
    print("\n" + "=" * 80)
    print("HR MANAGEMENT PLATFORM - TEST SUITE")
    print("=" * 80)
    
    try:
        # Test 1: Load
        handler, personale, strutture, db_tns_orig = test_load_data()
        
        # Test 2: Validation
        test_validation(personale, strutture)
        
        # Test 3: Merge
        db_tns = test_merge(personale, strutture)
        
        # Test 4: Save
        test_save(handler, personale, strutture, db_tns)
        
        print("\n" + "=" * 80)
        print("✅ TUTTI I TEST COMPLETATI CON SUCCESSO!")
        print("=" * 80)
        print("\n🚀 Avvia l'applicazione con: streamlit run app.py")
        
    except Exception as e:
        print(f"\n❌ ERRORE NEI TEST: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())

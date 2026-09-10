import pyodbc
import time
import os
from datetime import datetime
from fpdf import FPDF


DB_SERVER = r'DESKTOP-KTG1VDT\INSERTNEXO'
DB_NAME = 'Nexo_Demo_1'

def generuj_zbiorczy_pdf(lista_roslin, numer_faktury, dok_id):
    """Generuje dokument PDF z siatką paszportów (do 8 sztuk na stronie A4)."""
    
   
    numer_rejestracyjny = "XX-XX/XX/XXXX"  
    
    try:
        
        pdf = FPDF(format='A4')
        
        pdf.add_font('Arial', '', r'C:\Windows\Fonts\arial.ttf')
        pdf.add_font('Arial', 'B', r'C:\Windows\Fonts\arialbd.ttf')
        
        czy_jest_flaga = os.path.exists('flaga.jpg')
        if not czy_jest_flaga:
            print("[OSTRZEŻENIE] Nie znaleziono pliku flaga.jpg w folderze ze skryptem!")

        pdf.add_page()
        
        for indeks, roslina in enumerate(lista_roslin):
            if indeks > 0 and indeks % 8 == 0:
                pdf.add_page()
            
            pozycja_na_stronie = indeks % 8
            kolumna = pozycja_na_stronie % 2
            rzad = pozycja_na_stronie // 2
            
            x_offset = 10 + (kolumna * 100) 
            y_offset = 10 + (rzad * 70)
            
            pdf.rect(x_offset, y_offset, 90, 60)
            
            if czy_jest_flaga:
                pdf.image('flaga.jpg', x_offset + 2, y_offset + 2, 20) 
            
            pdf.set_font('Arial', 'B', 11)
            pdf.set_xy(x_offset + 25, y_offset + 3); pdf.cell(0, 5, "Paszport roślin /")
            pdf.set_xy(x_offset + 25, y_offset + 8); pdf.cell(0, 5, "Plant Passport")
        
            pdf.set_font('Arial', 'B', 12)
            pdf.set_xy(x_offset + 2, y_offset + 18); pdf.cell(10, 5, "A")
            pdf.set_xy(x_offset + 2, y_offset + 27); pdf.cell(10, 5, "B")
            pdf.set_xy(x_offset + 2, y_offset + 36); pdf.cell(10, 5, "C")
            pdf.set_xy(x_offset + 2, y_offset + 45); pdf.cell(10, 5, "D")
    
            pdf.set_font('Arial', '', 10)
            pdf.set_xy(x_offset + 10, y_offset + 18); pdf.cell(0, 5, roslina)
            pdf.set_xy(x_offset + 10, y_offset + 27); pdf.cell(0, 5, numer_rejestracyjny)
            pdf.set_xy(x_offset + 10, y_offset + 36); pdf.cell(0, 5, numer_faktury)
            pdf.set_xy(x_offset + 10, y_offset + 45); pdf.cell(0, 5, "PL")
        
        pulpit = os.path.join(os.environ['USERPROFILE'], 'Desktop')
        bezpieczny_numer = numer_faktury.replace('/', '_').replace(' ', '_')
        nazwa_pliku = f"Paszporty_{bezpieczny_numer}.pdf"
        pelna_sciezka = os.path.join(pulpit, nazwa_pliku)
        
        pdf.output(pelna_sciezka)
        print(f"[OK] Zapisano zbiorczy PDF na pulpicie: {nazwa_pliku}")
        
    except Exception as e:
        print(f"[BŁĄD] Wystąpił problem przy generowaniu PDF: {e}")

def pobierz_nowe_rosliny(cursor, last_id):
    query = """
        SELECT 
            d.Id AS DokumentId, 
            a.Nazwa AS NazwaAsortymentu, 
            a.Uwagi AS UwagiAsortymentu,
            p.Ilosc, 
            d.NumerWewnetrzny_PelnaSygnatura AS NumerFaktury
        FROM ModelDanychContainer.Dokumenty d
        INNER JOIN ModelDanychContainer.PozycjeDokumentu p ON p.Dokument_Id = d.Id
        INNER JOIN ModelDanychContainer.Asortymenty a ON p.AsortymentAktualnyId = a.Id
        INNER JOIN ModelDanychContainer.GrupyAsortymentu g ON a.Grupa_Id = g.Id
        WHERE d.Symbol = 'FS' 
          AND g.Nazwa <> 'Komplet' 
          AND d.Id > ?
        ORDER BY d.Id ASC
    """
    cursor.execute(query, last_id)
    return cursor.fetchall()

def main():
    conn_str = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={DB_SERVER};DATABASE={DB_NAME};Trusted_Connection=yes;TrustServerCertificate=yes;'
    
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        print(f"Połączono z bazą {DB_NAME} na serwerze {DB_SERVER}.")
    except pyodbc.Error as e:
        print(f"Błąd połączenia z bazą SQL: {e}")
        return

    try:
        cursor.execute("SELECT ISNULL(MAX(Id), 0) FROM ModelDanychContainer.Dokumenty WHERE Symbol = 'FS'")
        last_id = cursor.fetchone()[0]
        print(f"Gotowy. Czekam na nowe faktury (Startuje od ID: {last_id})...\n")
    except Exception as e:
        print(f"Błąd przy odczycie struktury bazy: {e}")
        return

    while True:
        try:
            nowe_pozycje = pobierz_nowe_rosliny(cursor, last_id)
            
            if nowe_pozycje:
                faktury_do_wydruku = {}
                
                for wiersz in nowe_pozycje:
                    dok_id = wiersz.DokumentId
                    nazwa_oryginalna = wiersz.NazwaAsortymentu
                    uwagi = wiersz.UwagiAsortymentu
                    numer_faktury = wiersz.NumerFaktury
                    
                    if uwagi and uwagi.strip():
                        nazwa_na_paszport = uwagi.strip()
                    else:
                        nazwa_na_paszport = nazwa_oryginalna
                    
                    if dok_id not in faktury_do_wydruku:
                        faktury_do_wydruku[dok_id] = {
                            'numer': numer_faktury, 
                            'rosliny': []
                        }
                    
                    faktury_do_wydruku[dok_id]['rosliny'].append(nazwa_na_paszport)
                    
                    if dok_id > last_id:
                        last_id = dok_id

                for id_dokumentu, dane in faktury_do_wydruku.items():
                    print(f"Wykryto fakturę: {dane['numer']} zawierającą {len(dane['rosliny'])} pozycje(i) (pomijam komplety).")
                    generuj_zbiorczy_pdf(dane['rosliny'], dane['numer'], id_dokumentu)

            time.sleep(5) 

        except KeyboardInterrupt:
            print("\nZatrzymano skrypt.")
            break
        except Exception as e:
            print(f"Błąd podczas odpytywania bazy: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
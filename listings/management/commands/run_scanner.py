import time
from django.core.management.base import BaseCommand
from listings.services.scraper_service import scan_all_active_targets


class Command(BaseCommand):
    help = "Sahibinden uzerindeki tum aktif arama hedeflerini tarar ve eslesenleri Telegram ile bildirir."

    def add_arguments(self, parser):
        parser.add_argument(
            '--loop',
            action='store_true',
            help='Surekli arka plan dongusunde calistirir'
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=5,
            help='Dongu calisma araligi (dakika cinsinden, varsayilan: 5)'
        )

    def handle(self, *args, **options):
        is_loop = options.get('loop', False)
        interval = options.get('interval', 5)

        self.stdout.write(self.style.SUCCESS("[BulBana] Ilan Tarama Motoru Baslatildi!"))

        if not is_loop:
            self.stdout.write("[*] Tek seferlik tarama yapiliyor...")
            results = scan_all_active_targets()
            self.stdout.write(self.style.SUCCESS(f"[OK] Tarama tamamlandi. Sonuc: {results}"))
            return

        self.stdout.write(self.style.WARNING(f"[!] Dongu modu aktif: Her {interval} dakikada bir taranacak."))
        try:
            while True:
                self.stdout.write(f"\n[*] {time.strftime('%H:%M:%S')} - Aktif hedefler kontrol ediliyor...")
                results = scan_all_active_targets()
                for res in results:
                    self.stdout.write(f" -> {res['target']}: {res['result']}")
                self.stdout.write(f"[+] {interval} dakika bekleniyor...\n")
                time.sleep(interval * 60)
        except KeyboardInterrupt:
            self.stdout.write(self.style.SUCCESS("\n[!] Tarama motoru durduruldu."))

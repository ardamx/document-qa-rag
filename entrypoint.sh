#!/bin/bash
# Ollama sunucusunu arka planda başlat
ollama serve &

# Sunucunun ayağa kalkmasını bekle
until ollama list >/dev/null 2>&1; do
  sleep 1
done

# Modeli çek (volume'da zaten varsa indirme yapmadan geçer)
ollama pull gemma3:12b-it-q4_K_M

# Arka plandaki sunucuyu ön plana al (container açık kalsın)
wait

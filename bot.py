import asyncio
import discord
from discord.ext import commands

import config
import logic

logic.init_db()

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Bot berhasil masuk sebagai {bot.user.name}")

class AddressModal(discord.ui.Modal, title="Input Alamat Pengiriman"):
    address_input = discord.ui.TextInput(
        label="Alamat Lengkap",
        style=discord.TextStyle.paragraph,
        placeholder="Masukkan jalan, kota, kode pos, dll...",
        required=True,
        max_length=300
    )

    def __init__(self, cart_items):
        super().__init__()
        self.cart_items = cart_items

    async def on_submit(self, interaction: discord.Interaction):
        logic.set_user_address(interaction.user.id, self.address_input.value)
        await interaction.response.send_message("Alamat berhasil disimpan! Melanjutkan proses checkout...", ephemeral=True)
        await process_payment(interaction, self.cart_items, self.address_input.value)

# view tombol konfirmasi bayar
class PaymentView(discord.ui.View):
    def __init__(self, user_id, total_price):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.total_price = total_price

    @discord.ui.button(label="Saya Sudah Bayar", style=discord.ButtonStyle.success)
    async def confirm_payment(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Ini bukan sesi transaksi Anda.", ephemeral=True)
            return

        # Simpan transaksi & kosongkan keranjang
        logic.create_transaction(self.user_id, self.total_price)
        logic.clear_user_cart(self.user_id)
        
        # Nonaktifkan tombol setelah diklik
        button.disabled = True
        await interaction.response.edit_message(view=self)

        await interaction.followup.send(
            f"✅ **Pembayaran berhasil dikonfirmasi!**\n"
            f"Terima kasih **{interaction.user.name}**, pesanan Anda sedang diproses dan barang akan segera dikirim!"
        )

# helper fungsi pembayaran
async def process_payment(interaction_or_ctx, cart_items, address):
    user = interaction_or_ctx.user if isinstance(interaction_or_ctx, discord.Interaction) else interaction_or_ctx.author
    
    total = 0
    item_details = []
    for item in cart_items:
        final_price = item['price'] * (1 - item['discount'] / 100)
        subtotal = final_price * item['quantity']
        total += subtotal
        disc_text = f" (Diskon {item['discount']}%)" if item['discount'] > 0 else ""
        item_details.append(f"• **{item['name']}** x{item['quantity']} - Rp {subtotal:,.0f}{disc_text}")

    embed = discord.Embed(
        title="🧾 Ringkasan & Instruksi Pembayaran",
        color=discord.Color.gold()
    )
    embed.add_field(name="📍 Alamat Pengiriman", value=address, inline=False)
    embed.add_field(name="📦 Daftar Barang", value="\n".join(item_details), inline=False)
    embed.add_field(name="💰 Total Pembayaran", value=f"**Rp {total:,.0f}**", inline=False)
    
    embed.add_field(
        name="🏦 Transfer Bank", 
        value=f"**{config.BANK_NAME}**\nNo. Rek: `{config.BANK_ACCOUNT_NUMBER}`\na.n. {config.BANK_ACCOUNT_NAME}", 
        inline=False
    )
    embed.set_image(url=config.QR_CODE_URL)
    embed.set_footer(text="Silakan lakukan transfer lalu tekan tombol di bawah ini.")

    view = PaymentView(user.id, total)
    
    if isinstance(interaction_or_ctx, discord.Interaction):
        await interaction_or_ctx.followup.send(embed=embed, view=view)
    else:
        await interaction_or_ctx.send(embed=embed, view=view)

# perintah

@bot.command(name="products")
async def show_products(ctx):
    products = logic.get_all_products()
    if not products:
        await ctx.send("Belum ada produk yang tersedia.")
        return

    embed = discord.Embed(title="🛍️ Daftar Semua Produk", color=discord.Color.blue())
    for p in products:
        price_text = f"Rp {p['price']:,.0f}"
        if p['discount'] > 0:
            discounted = p['price'] * (1 - p['discount'] / 100)
            price_text = f"~~Rp {p['price']:,.0f}~~ **Rp {discounted:,.0f}** (-{p['discount']}%)"
        
        embed.add_field(
            name=p['name'],
            value=f"Kategori: {p['category']} | Ukuran: {p['size']}\nHarga: {price_text}",
            inline=False
        )
    await ctx.send(embed=embed)

@bot.command(name="category")
async def show_categories(ctx):
    categories = logic.get_all_categories()
    if not categories:
        await ctx.send("Belum ada kategori produk.")
        return
    
    desc = "\n".join([f"• {c}" for c in categories])
    embed = discord.Embed(title="🏷️ Kategori Produk", description=desc, color=discord.Color.green())
    await ctx.send(embed=embed)

@bot.command(name="product")
async def show_by_category(ctx, *, category_name: str = None):
    if not category_name:
        await ctx.send("Harap masukkan nama kategori. Contoh: `!product Pakaian`")
        return

    products = logic.get_products_by_category(category_name)
    if not products:
        await ctx.send(f"Tidak ada produk dalam kategori **{category_name}**.")
        return

    embed = discord.Embed(title=f"📦 Produk Kategori: {category_name.title()}", color=discord.Color.blue())
    for p in products:
        embed.add_field(
            name=p['name'],
            value=f"Ukuran: {p['size']} | Harga: Rp {p['price']:,.0f}",
            inline=False
        )
    await ctx.send(embed=embed)

@bot.command(name="detail")
async def show_detail(ctx, *, product_name: str = None):
    if not product_name:
        await ctx.send("Harap masukkan nama produk. Contoh: `!detail Kaos Polos`")
        return

    product = logic.get_product_by_name(product_name)
    if not product:
        await ctx.send(f"Produk **{product_name}** tidak ditemukan.")
        return

    p = product
    final_price = p['price'] * (1 - p['discount'] / 100)

    embed = discord.Embed(title=f"🔍 Detail Produk: {p['name']}", color=discord.Color.purple())
    embed.add_field(name="Kategori", value=p['category'], inline=True)
    embed.add_field(name="Ukuran", value=p['size'], inline=True)
    embed.add_field(name="Harga Normal", value=f"Rp {p['price']:,.0f}", inline=True)
    embed.add_field(name="Diskon", value=f"{p['discount']}%", inline=True)
    embed.add_field(name="Harga Akhir", value=f"**Rp {final_price:,.0f}**", inline=True)
    
    if p['image_url']:
        embed.set_image(url=p['image_url'])

    await ctx.send(embed=embed)

@bot.command(name="addtocart")
async def add_cart(ctx, *, product_name: str = None):
    if not product_name:
        await ctx.send("Harap masukkan nama produk. Contoh: `!addtocart Kaos Polos`")
        return

    product = logic.get_product_by_name(product_name)
    if not product:
        await ctx.send(f"Produk **{product_name}** tidak ditemukan.")
        return

    logic.add_to_cart(ctx.author.id, product['id'])
    await ctx.send(f"✅ **{product['name']}** berhasil ditambahkan ke keranjang!")

@bot.command(name="carts")
async def show_cart(ctx):
    items = logic.get_user_cart(ctx.author.id)
    if not items:
        await ctx.send("Keranjang belanja Anda masih kosong.")
        return

    embed = discord.Embed(title=f"🛒 Keranjang Belanja {ctx.author.name}", color=discord.Color.orange())
    total = 0
    for item in items:
        final_price = item['price'] * (1 - item['discount'] / 100)
        subtotal = final_price * item['quantity']
        total += subtotal
        embed.add_field(
            name=f"{item['name']} (x{item['quantity']})",
            value=f"Harga/unit: Rp {final_price:,.0f} | Subtotal: Rp {subtotal:,.0f}",
            inline=False
        )
    embed.add_field(name=" Total", value=f"**Rp {total:,.0f}**", inline=False)
    await ctx.send(embed=embed)

@bot.command(name="checkout")
async def checkout(ctx):
    cart_items = logic.get_user_cart(ctx.author.id)
    if not cart_items:
        await ctx.send("Keranjang belanja Anda kosong. Tambahkan barang terlebih dahulu.")
        return

    address = logic.get_user_address(ctx.author.id)

    # Jika alamat belum ada, tampilkan Modal melalui tombol
    if not address:
        class AddressPromptView(discord.ui.View):
            @discord.ui.button(label="Isi Alamat Pengiriman", style=discord.ButtonStyle.primary)
            async def open_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
                await interaction.response.send_modal(AddressModal(cart_items))

        await ctx.send("⚠️ Anda belum menyimpan alamat pengiriman. Silakan klik tombol di bawah untuk mengisi alamat:", view=AddressPromptView())
    else:
        await process_payment(ctx, cart_items, address)

bot.run(config.TOKEN)

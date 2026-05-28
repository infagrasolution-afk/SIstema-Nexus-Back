import asyncio
import base64
import os
import asyncpg

async def main():
    # Path to the uploaded logo file
    logo_path = r"C:\Users\USER\.gemini\antigravity\brain\b823314a-12d8-4a20-b977-2b826126f8b6\media__1779942542508.jpg"
    
    if not os.path.exists(logo_path):
        print(f"Error: File not found at {logo_path}")
        return
        
    print("Reading logo image...")
    with open(logo_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        
    base64_data = f"data:image/jpeg;base64,{encoded_string}"
    print("Base64 string generated successfully.")
    
    # Connect to PostgreSQL using asyncpg
    db_url = "postgresql://admin:nkj2VovKl0DDJgBZ1NonhTS6uLXxj5nu@dpg-d8b2pmcm0tmc73d5d6pg-a.virginia-postgres.render.com/erp_db_x91k"
    print("Connecting to database...")
    
    try:
        conn = await asyncpg.connect(db_url)
        print("Connected.")
        
        # Look for the tenant KPRISHOP
        row = await conn.fetchrow("SELECT id, name FROM tenants WHERE name ILIKE '%KPRISHOP%';")
        
        if not row:
            print("Error: KPRISHOP tenant not found in database!")
            await conn.close()
            return
            
        tenant_id = row['id']
        name = row['name']
        print(f"Found tenant: {name} (ID: {tenant_id})")
        
        # Update logo_url
        print("Updating logo_url in tenants table...")
        await conn.execute(
            "UPDATE tenants SET logo_url = $1 WHERE id = $2;",
            base64_data, tenant_id
        )
        print("Logo updated successfully in database!")
        
        await conn.close()
        print("Connection closed.")
        
    except Exception as e:
        print(f"Database error: {e}")

if __name__ == "__main__":
    asyncio.run(main())

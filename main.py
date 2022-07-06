from math import floor
import datetime
import discord
import logging
import os
import json
import time
from termcolor import colored
from dotenv import load_dotenv
import asyncio
import requests
from dictdiffer import diff

logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(
	filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter(
	'%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

load_dotenv()
hypixel_token = os.environ["HYPIXEL_TOKEN"]
discord_token = os.environ["DISCORD_TOKEN"]

request_params = {"key": hypixel_token,"uuid": "141e49cd3cd2475fabfb94086608b450"}
# 3Qi: d7e1874a714f46e08d2b0a5fa86311eb
# 5Of: 141e49cd3cd2475fabfb94086608b450

type_names = ("QUAKECRAFT", "WALLS", "PAINTBALL", "SURVIVAL_GAMES", "TNTGAMES", "VAMPIREZ", "WALLS3", "ARCADE", "ARENA", "UHC", "MCGO", "BATTLEGROUND", "SUPER_SMASH", "GINGERBREAD",
			  "HOUSING", "SKYWARS", "TRUE_COMBAT", "SPEED_UHC", "SKYCLASH", "LEGACY", "PROTOTYPE", "BEDWARS", "MURDER_MYSTERY", "BUILD_BATTLE", "DUELS", "SKYBLOCK", "PIT", "REPLAY", "SMP")
db_names = ("Quake", "Walls", "Paintball", "HungerGames", "TNTGames", "VampireZ", "Walls3", "Arcade", "Arena", "UHC", "MCGO", "Battleground", "SuperSmash", "GingerBread",
			"Housing", "SkyWars", "TrueCombat", "SpeedUHC", "SkyClash", "Legacy", "Prototype", "Bedwars", "MurderMystery", "BuildBattle", "Duels", "SkyBlock", "Pit", "Replay", "SMP")
clean_names = ("Quakecraft", "Walls", "Paintball", "Blitz Survival Games", "TNT Games", "VampireZ", "Mega Walls", "Arcade", "Arena Brawl", "UHC", "CVC", "Warlords", "Smash Heroes", "Turbo Kart Racers",
			   "Housing", "SkyWars", "Crazy Walls", "Speed UHC", "SkyClash", "Classic Games", "Prototype", "Bed Wars", "Murder Mystery", "Build Battle", "Duels", "SkyBlock", "Pit", "Replay", "SMP")

arena_modes = ()

def convert_to_lists(t):
	return list(map(convert_to_lists, t)) if isinstance(t, (list, tuple)) else t

def clean_name(name):
	for g in range(len(clean_names)):
		if name == type_names[g] or name == db_names[g] or name == clean_names[g]:
			return clean_names[g]

def readify(text):
	return text.replace("_", " ").title()

class BotClient(discord.Client):
	global prev_res, status_change, stat_change

	async def post_log(content, channel=991131293909782558):
		await client.get_channel(channel).send(content="**<t:{0}:d> @ <t:{0}:T>** \u27eb ".format(str(floor(time.time())))+str(content))

	async def status_change(r, pr):
		match r["online"]:
			case True:
				match r.get("map"):
					case None:
						if r["mode"] == "LOBBY" and not pr["online"]:
							await BotClient.post_log(f'Joined Hypixel and entered the {clean_name(r["gameType"])} lobby.', 991322369291452517)
						else:
							await BotClient.post_log(f'Joined the {clean_name(r["gameType"])} lobby.', 991322369291452517)
					case "Duel Arena":
						await BotClient.post_log("Pulled up to Duels Arena.", 991322369291452517)
					case _:
						parsed_mode = readify(r["mode"])
						if r["mode"] == pr["mode"]:
							await BotClient.post_log(f'Requeued {parsed_mode} to the map {r["map"]}.', 991322369291452517)
						elif r["mode"] != pr["mode"] or not pr["online"]:
							await BotClient.post_log(f'Queued {clean_name(r["gameType"])} in {parsed_mode} on the map {r["map"]}', 991322369291452517)
			case False:
				await BotClient.post_log("Left Hypixel", 991322369291452517)

	async def stat_change(r, pr):
		new_diff = convert_to_lists(list(diff(pr, r)))
		new_diffs = []
		for i in range(len(new_diff)):
			try:
				del new_diff[i][0]
			except IndexError:
				await BotClient.post_log("IndexError! at " + str(i))
				break
			try:
				if type(new_diff[i][1][0]) == int and type(new_diff[i][1][1]) == int:
					# numeric change in duels arena
					first_value = new_diff[i][1][0]
					second_value = new_diff[i][1][1]

					match new_diff[i][0]:
						case "best_winstreak_mode_duel_arena":
							new_diffs.append(["Best Winstreak", f'{first_value} \u279c {second_value}', False])
						case "current_winstreak_mode_duel_arena":
							new_diffs.append(["Current Winstreak", f'{first_value} \u279c {second_value}', False])
						case _:
							if new_diff[i][0][:11] == "duel_arena_":
								if first_value > second_value: # decrease??!
									change_str = str(second_value - first_value)
								else: # increase.
									change_str = "+" + str(second_value - first_value)
								new_diffs.append([f"{readify(new_diff[i][0][11:])}", change_str])
				elif type(new_diff[i][1][0] != int): #not a number change
					if len(new_diff[i][1]) == 2 and new_diff[i][0][:10]=="arena_mode":
						new_diffs.append([f'{readify(new_diff[i][0][11:])} preference', f'{str(new_diff[i][1][0])} \u279c {str(new_diff[i][1][1])}'])
					elif len(new_diff[i][1]) == 1: # new data
						new_diffs.append([f"{str(new_diff[i][1])}", "Added/removed"])
			except ValueError: # LIST change
				new_diffs.append([{new_diff[i][0]}, f"{str(new_diff[i][1][0])} to {str(new_diff[i][1][1])}"])
		if new_diffs != []:
			stat_embed = discord.Embed(
				title="**<t:{0}:d> @ <t:{0}:T>**".format(str(floor(time.time()))),
				color=discord.Colour.dark_green()
			)

			for changed_stat in new_diffs:
				try:
					make_inline = changed_stat[2]
				except IndexError:
					make_inline = True
				stat_embed.add_field(name=changed_stat[0], value=changed_stat[1], inline=make_inline)
			await client.get_channel(991131293909782558).send(embed=stat_embed)

	async def on_ready(self):
		print(colored('Logged on as {0}!'.format(self.user), "blue"))
		await BotClient.post_log("Discord bot restarted")

		activity = discord.Activity(name="Duels Arena", type=discord.ActivityType.playing)
		
		async def playercount_periodic():
			requested_counts = json.loads(requests.get(
				"http://api.hypixel.net/counts",
				params={"key":hypixel_token}
			).text)
			if requested_counts["success"]:
				count = requested_counts["games"]
				updated_timestamp = floor(time.time())
				counts = [
					["Total", requested_counts["playerCount"]],
					["Duels", count["DUELS"]["players"]],
					["Duels Arena", count["DUELS"]["modes"].get("DUELS_DUEL_ARENA")],
					["Skywars 1v1", count["DUELS"]["modes"].get("DUELS_SW_DUEL")],
					["Skywars 2v2", count["DUELS"]["modes"].get("DUELS_SW_DOUBLES")],
					["Bridge 4v4", count["DUELS"]["modes"].get("DUELS_BRIDGE_FOUR")],
					["VampireZ", count["LEGACY"]["modes"].get("VAMPIREZ")],
					["Walls", count["LEGACY"]["modes"].get("WALLS")],
					["TKR", count["LEGACY"]["modes"].get("GINGERBREAD")]
				]
				
				counts_embed = discord.Embed(
					title="Hypixel Current Player Counts",
					description=f"Last updated: <t:{str(updated_timestamp)}:R>",
					color=discord.Colour.dark_green()
				) 
				# counts_embed.set_author(name=f"Last updated: <t:{str(updated_timestamp)}:R>")
				for count_mode in counts:
					counts_embed.add_field(name=count_mode[0], value=count_mode[1], inline=True)

				counts_message = await client.get_channel(991861424550850560).fetch_message(991863952063594606)
				await counts_message.edit(content="", embed=counts_embed)
			else:
				await BotClient.post_log("Error! During checking player counts: " + requested_counts["cause"])

		async def account_periodic():
			global res, prev_res
			try: 
				with open("saved_data.json", "r", encoding="utf-8") as prev_data:
					prev_res = json.load(prev_data)
				try:
					res = {
						"status": json.loads(requests.get(
							"http://api.hypixel.net/status",
							params=request_params
						).text),
						"stat": json.loads(requests.get(
							"http://api.hypixel.net/player",
							params=request_params
						).text)
					}
				except Exception as err:
					await BotClient.post_log("Error! In API request: " + str(err.args))

				if res != prev_res:  # on player change!
					match res["status"]["success"]:
						case True:
							major_change = False
							if res["status"]["session"] != prev_res["status"]["session"]:
								major_change = True
								await status_change(res["status"]["session"], prev_res["status"]["session"])
							if res["stat"]["player"]["stats"]["Duels"] != prev_res["stat"]["player"]["stats"]["Duels"]:
								major_change = True
								await stat_change(res["stat"]["player"]["stats"]["Duels"], prev_res["stat"]["player"]["stats"]["Duels"])
							if major_change:
								with open("saved_data.json", "w", encoding="utf-8") as f:
									print("WRITING to file!")
									json.dump(res, f, ensure_ascii=False, indent=4)
							
						case False:
							await BotClient.post_log("Error! " + res["status"]["cause"])
				prev_res = res
				await asyncio.sleep(5)
			except Exception as err:
				await BotClient.post_log("Error! " + str(err.args))
		
		def account_async():
			loop = asyncio.get_event_loop()
			loop.call_later(5, account_async)
			task = loop.create_task(account_periodic())
			try:
				loop.run_forever(task)
			except:
				pass
		
		def playercount_async():
			playercount_loop = asyncio.get_event_loop()
			playercount_loop.call_later(18, playercount_async)
			playercount_task = playercount_loop.create_task(playercount_periodic())
			try:
				playercount_loop.run_forever(playercount_task)
			except:
				pass

		account_async()
		playercount_async()

	async def on_message(self, message):
		if message.author != self.user and message.content[:11] == "%arenapref ":
			print("modes request for " + message.content[11:])
			requested_uuid = requests.get("https://api.mojang.com/users/profiles/minecraft/" + message.content[11:]).text
			if len(requested_uuid):
				requested_ign = json.loads(requested_uuid)["name"]
				requested_player_response = json.loads(requests.get(
					"http://api.hypixel.net/player",
					params={"key": hypixel_token, "uuid": json.loads(requested_uuid)["id"]}
				).text) # name: username with right caps, id: uuid
				if requested_player_response["player"] and requested_player_response["player"]["stats"]["Duels"].get("arena_mode_uhc"):
					duels_stats = requested_player_response["player"]["stats"]["Duels"]
					modes = ("uhc", "op", "classic", "bow", "no_debuff", "soup")
					mode_emotes = {"uhc": "<:UHC:994047777568981012>",
						"op": "<:OP:994047775056605184>",
						"classic": "<:Classic:994047773102047272>",
						"bow": "<:Bow:994047772170919976>",
						"no_debuff": "<:NDB:994047774037397564>",
						"soup": "<:Soup:994047776474267678>"
					}
					
					prefs = f'Preferences for {requested_ign}:'
					for mode in modes:
						prefs += f'\n{mode_emotes[mode]} {duels_stats.get("arena_mode_" + mode)}'
			
					await message.channel.send(prefs)
				else:
					await message.channel.send("That player has never played Duels Arena.")
			else:
				await message.channel.send("That player doesn't exist.")
		elif message.author != self.user and message.content[:5] == "%ping":
			message_coro = await message.channel.send(':ping_pong: Pinging...')
			message_sent = await message.channel.fetch_message(message_coro.id)
			timestamp_delta = (message_sent.created_at-message.created_at).total_seconds()
			
			await message_sent.edit(content=':ping_pong: Pong! It took {}ms'.format(int(timestamp_delta*500)))
		elif message.author != self.user and (message.content == "%kill" or message.content == "%quit"):
			await message.add_reaction("☑️")
			await client.close()
			print(colored("CLIENT CLOSED", "red"))
		
		if "lil vro" in message.content.lower():
			await message.add_reaction("<a:onglilvro:992574992556490814>")
client = BotClient()
client.run(discord_token)

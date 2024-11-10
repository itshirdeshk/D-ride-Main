from flask import Flask, request, jsonify
from uagents import Agent, Bureau, Context, Model
import asyncio

app = Flask(__name__)

# Define negotiation model
class OfferMessage(Model):
    price: float
    location: str
    round: int  # Track negotiation rounds

user_agent = Agent(name="user_agent", seed="user_seed_phrase")
driver_agent = Agent(name="driver_agent", seed="driver_seed_phrase")

# Define preferences and parameters
user_max_price = 24.0
driver_min_price = 25.0
max_rounds = 5

# Flask route for starting negotiation
@app.route('/start_negotiation', methods=['POST'])
def start_negotiation():
    data = request.json
    location = data.get("location", "Downtown")
    initial_price = data.get("initial_price", 15.0)
    
    # Create an asyncio task to initiate the negotiation asynchronously
    asyncio.run(initiate_negotiation(initial_price, location))
    
    return jsonify({"status": "Negotiation started", "initial_price": initial_price, "location": location})

async def initiate_negotiation(initial_price, location):
    initial_offer = OfferMessage(price=initial_price, location=location, round=1)
    user_agent.context.logger.info(f"[User] Sending initial offer: ${initial_offer.price} at {initial_offer.location}")
    await user_agent.context.send(driver_agent.address, initial_offer)

@user_agent.on_message(model=OfferMessage)
async def handle_counteroffer(ctx: Context, sender: str, msg: OfferMessage):
    ctx.logger.info(f"[User] Received counteroffer: ${msg.price} at {msg.location} (Round {msg.round})")
    
    if msg.price <= user_max_price and msg.round < max_rounds:
        if msg.price > initial_offer.price:
            final_offer = OfferMessage(price=msg.price, location=msg.location, round=msg.round + 1)
            ctx.logger.info(f"[User] Accepting offer at ${final_offer.price}")
        else:
            ctx.logger.info(f"[User] Initial offer accepted.")
    else:
        if msg.round < max_rounds:
            next_offer = OfferMessage(price=min(msg.price - 0.5, user_max_price), location=msg.location, round=msg.round + 1)
            ctx.logger.info(f"[User] Sending counteroffer: ${next_offer.price}")
            await ctx.send(driver_agent.address, next_offer)
        else:
            ctx.logger.info("[User] Ending negotiation - offer exceeded max rounds or max price.")

@driver_agent.on_message(model=OfferMessage)
async def handle_offer(ctx: Context, sender: str, msg: OfferMessage):
    ctx.logger.info(f"[Driver] Received offer: ${msg.price} at {msg.location} (Round {msg.round})")
    
    if msg.price >= driver_min_price:
        ctx.logger.info(f"[Driver] Offer accepted at ${msg.price}")
        accepted_offer = OfferMessage(price=msg.price, location=msg.location, round=msg.round + 1)
        await ctx.send(user_agent.address, accepted_offer)
    else:
        if msg.round < max_rounds:
            counter_offer_price = max(msg.price + 1.0, driver_min_price)
            counter_offer = OfferMessage(price=counter_offer_price, location=msg.location, round=msg.round + 1)
            ctx.logger.info(f"[Driver] Sending counteroffer: ${counter_offer.price}")
            await ctx.send(user_agent.address, counter_offer)
        else:
            ctx.logger.info("[Driver] Ending negotiation - offer too low after max rounds.")

# Run the Flask app and the Bureau concurrently
if __name__ == "__main__":
    bureau = Bureau()
    bureau.add(user_agent)
    bureau.add(driver_agent)

    # Start the Bureau in a separate thread to allow Flask and Bureau to run simultaneously
    from threading import Thread
    Thread(target=lambda: bureau.run()).start()
    app.run(port=5000)

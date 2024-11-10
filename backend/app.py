from uagents import Agent, Bureau, Context, Model
import random

class OfferMessage(Model):
    price: float
    location: str
    round: int
    status: str
    user_priority: str  # 'high', 'medium', 'low'
    driver_trust_score: float  # 0.0 to 1.0
    user_history_score: float  # Based on previous reviews (0.0 to 1.0)
    driver_rating: float  # Driver's rating (0.0 to 5.0)
    vehicle_type: str  # 'Standard', 'Luxury', 'SUV'
    weather: str  # 'clear', 'rainy', 'snowy'
    traffic: str  # 'low', 'medium', 'high'
    payment_method: str  # 'cash', 'credit'
    distance_km: float  # Distance in kilometers
    estimated_duration_min: int  # Estimated duration in minutes
    competition_factor: float  # 1.0 (low competition) to 0.7 (high competition)

user_agent = Agent(name="user_agent", seed="user_agent", endpoint=None)
driver_agent = Agent(name="driver_agent", seed="driver_agent", endpoint=None)

# User and driver preferences
user_max_price = 20.0
user_initial_offer = 15.0
user_priority = "medium"  # Flexibility in urgency
user_history_score = 0.85  # High user rating
driver_min_price = 22.0
driver_trust_score = 0.8
location_factor = {"Downtown": 1.0, "Suburb": 1.1}
max_rounds = 5
user_vehicle_preference = "Standard"
current_weather = "rainy"
current_traffic = "high"
current_payment_method = "credit"
competition_factor = 0.8  # Indicates moderate competition

@user_agent.on_event("startup")
async def start_negotiation(ctx: Context):
    initial_offer = OfferMessage(
        price=user_initial_offer,
        location="Noida",
        round=1,
        status='pending',
        user_priority=user_priority,
        driver_trust_score=driver_trust_score,
        user_history_score=user_history_score,
        driver_rating=4.3,
        vehicle_type=user_vehicle_preference,
        weather=current_weather,
        traffic=current_traffic,
        payment_method=current_payment_method,
        distance_km=5.0,
        estimated_duration_min=15,
        competition_factor=competition_factor
    )
    ctx.logger.info(f"[User] Sending initial offer: ${initial_offer.price} at {initial_offer.location}")
    await ctx.send(driver_agent.address, initial_offer)

@user_agent.on_message(model=OfferMessage)
async def handle_counteroffer(ctx: Context, sender: str, msg: OfferMessage):
    ctx.logger.info(f"[User] Received counteroffer: ₹{msg.price} at {msg.location} (Round {msg.round})")

    if msg.status == 'accepted':
        ctx.logger.info(f"[User] Negotiation completed successfully at ${msg.price}")
        return
    elif msg.status == 'rejected':
        ctx.logger.info("[User] Driver rejected offer. Ending negotiation.")
        return

    # Adjust acceptable price based on various conditions
    acceptable_price = user_max_price
    if msg.weather == "rainy":
        acceptable_price += 1.5  # Willing to pay more in bad weather
    if msg.traffic == "high":
        acceptable_price += 1.0  # Willing to pay more in high traffic
    if msg.payment_method == "cash":
        acceptable_price -= 0.5  # Cash discount
    if msg.round > 3 and user_priority == "medium":
        acceptable_price += 0.5  # Increase flexibility as rounds increase

    # Calculate next offer if within acceptable range
    if msg.price <= acceptable_price and msg.round < max_rounds:
        final_offer = OfferMessage(
            price=msg.price,
            location=msg.location,
            round=msg.round,
            status='accepted',
            user_priority=user_priority,
            driver_trust_score=driver_trust_score,
            user_history_score=user_history_score,
            driver_rating=msg.driver_rating,
            vehicle_type=msg.vehicle_type,
            weather=msg.weather,
            traffic=msg.traffic,
            payment_method=msg.payment_method,
            distance_km=msg.distance_km,
            estimated_duration_min=msg.estimated_duration_min,
            competition_factor=msg.competition_factor
        )
        ctx.logger.info(f"[User] Accepting offer at ${final_offer.price}")
        await ctx.send(driver_agent.address, final_offer)
    else:
        next_offer_price = min(msg.price - 0.7, acceptable_price)
        next_offer_price *= msg.competition_factor  # Adjust based on driver competition

        next_offer = OfferMessage(
            price=next_offer_price,
            location=msg.location,
            round=msg.round + 1,
            status='pending',
            user_priority=user_priority,
            driver_trust_score=driver_trust_score,
            user_history_score=user_history_score,
            driver_rating=msg.driver_rating,
            vehicle_type=msg.vehicle_type,
            weather=msg.weather,
            traffic=msg.traffic,
            payment_method=msg.payment_method,
            distance_km=msg.distance_km,
            estimated_duration_min=msg.estimated_duration_min,
            competition_factor=msg.competition_factor
        )
        ctx.logger.info(f"[User] Sending counteroffer: ${next_offer.price}")
        await ctx.send(driver_agent.address, next_offer)

@driver_agent.on_message(model=OfferMessage)
async def handle_offer(ctx: Context, sender: str, msg: OfferMessage):
    ctx.logger.info(f"[Driver] Received offer: ${msg.price} at {msg.location} (Round {msg.round})")
    
    if msg.status == 'accepted':
        ctx.logger.info(f"[Driver] Negotiation completed with accepted offer: ${msg.price}")
        return
    elif msg.status == 'rejected':
        ctx.logger.info(f"[Driver] Negotiation ended with rejection at round {msg.round}")
        return

    # Adjust minimum price based on conditions
    adjusted_min_price = driver_min_price
    if msg.weather == "rainy" or msg.weather == "snowy":
        adjusted_min_price += 1.5  # Increase price in bad weather
    if msg.traffic == "high":
        adjusted_min_price += 1.0  # Increase price in high traffic
    if msg.vehicle_type == "Luxury":
        adjusted_min_price += 3.0  # Add premium for luxury vehicles
    if msg.distance_km > 10:
        adjusted_min_price += 1.0  # Extra for long distances
    if msg.payment_method == "cash":
        adjusted_min_price -= 0.5  # Cash discount

    # Apply competition factor if applicable
    adjusted_min_price *= msg.competition_factor

    # Negotiate based on adjusted prices
    if msg.price >= adjusted_min_price:
        ctx.logger.info(f"[Driver] Offer accepted at ${msg.price}")
        await ctx.send(user_agent.address, OfferMessage(
            price=msg.price, location=msg.location, round=msg.round, status='accepted',
            user_priority=user_priority, driver_trust_score=driver_trust_score,
            user_history_score=user_history_score, driver_rating=msg.driver_rating,
            vehicle_type=msg.vehicle_type, weather=msg.weather, traffic=msg.traffic,
            payment_method=msg.payment_method, distance_km=msg.distance_km,
            estimated_duration_min=msg.estimated_duration_min, competition_factor=msg.competition_factor
        ))
    else:
        if msg.round < max_rounds:
            counter_offer_price = max(msg.price + 1.0, adjusted_min_price)
            counter_offer = OfferMessage(
                price=counter_offer_price,
                location=msg.location,
                round=msg.round + 1,
                status='pending',
                user_priority=user_priority,
                driver_trust_score=driver_trust_score,
                user_history_score=user_history_score,
                driver_rating=msg.driver_rating,
                vehicle_type=msg.vehicle_type,
                weather=msg.weather,
                traffic=msg.traffic,
                payment_method=msg.payment_method,
                distance_km=msg.distance_km,
                estimated_duration_min=msg.estimated_duration_min,
                competition_factor=msg.competition_factor
            )
            ctx.logger.info(f"[Driver] Sending counteroffer: ${counter_offer.price}")
            await ctx.send(user_agent.address, counter_offer)
        else:
            ctx.logger.info("[Driver] Ending negotiation - offer too low after max rounds.")
            final_message = OfferMessage(
                price=msg.price,
                location=msg.location,
                round=msg.round,
                status='rejected',
                user_priority=user_priority,
                driver_trust_score=driver_trust_score,
                user_history_score=user_history_score,
                driver_rating=msg.driver_rating,
                vehicle_type=msg.vehicle_type,
                weather=msg.weather,
                traffic=msg.traffic,
                payment_method=msg.payment_method,
                distance_km=msg.distance_km,
                estimated_duration_min=msg.estimated_duration_min,
                competition_factor=msg.competition_factor
            )
            await ctx.send(user_agent.address, final_message)

# Initialize bureau
bureau = Bureau(endpoint="http://127.0.0.1:8002", port=8002)
bureau.add(user_agent)
bureau.add(driver_agent)

if __name__ == "__main__":
    try:
        bureau.run()
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
    except Exception as e:
        print(f"Error occurred: {e}")

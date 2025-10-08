def resolve_horizontal(player, platforms):
    """Resolve horizontal collisions between player and platforms."""
    player.rect.x = int(player.x)
    for plat in platforms:
        if player.rect.colliderect(plat):
            if player.vx > 0:
                player.rect.right = plat.left
            elif player.vx < 0:
                player.rect.left = plat.right
            player.x = player.rect.x

def resolve_vertical(player, platforms):
    """Resolve vertical collisions between player and platforms."""
    player.rect.y = int(player.y)
    on_ground = False
    for plat in platforms:
        if player.rect.colliderect(plat):
            if player.vy > 0:
                # falling -> land on top
                player.rect.bottom = plat.top
                player.vy = 0
                player.y = player.rect.y
                on_ground = True
                # refill jumps when landing
                player.jumps_remaining = player.max_jumps
            elif player.vy < 0:
                # hit bottom of platform
                player.rect.top = plat.bottom
                player.vy = 0
                player.y = player.rect.y
    return on_ground

def clamp_player_to_level(player, level_width, level_height):
    """Keep player within level bounds."""
    # clamp player within horizontal level bounds
    if player.rect.left < 0:
        player.rect.left = 0
        player.x = player.rect.x
    if player.rect.right > level_width:
        player.rect.right = level_width
        player.x = player.rect.x

    # clamp player vertically
    if player.rect.top < 0:
        player.rect.top = 0
        player.y = player.rect.y
    if player.rect.bottom > level_height:
        player.rect.bottom = level_height
        player.y = player.rect.y
        player.vy = 0
        player.jumps_remaining = player.max_jumps

    # keep player rect synchronized
    player.rect.x = int(player.x)
    player.rect.y = int(player.y)
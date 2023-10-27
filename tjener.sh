#!/usr/bin/env bash
# Author: Hans Fleischer 01/09/2023
# Skript for å håndtere start/stop/debug av web_tjener.
# Finner PID til ./web_tjener og dreper den med kill-kommandoen, eller
# kompilerer og starter web_tjener i debug eller standard modus.
WRKDIR=/opt/web_server
ROTFS="/opt/web_server/container"
DAEMON_PID=$(ps aux | grep "./web_tjener" | grep -v grep | awk '{print $2}')
CONTAINER_PID=$(ps aux | grep "init" | grep -v grep | grep -v sbin | awk '{print $2}')

# Unshare-konteiner som kjøres som en upriviligert bruker
unshare_tjener () {
    # Oppretter mapper for container
    mkdir -p $ROTFS/bin $ROTFS/proc $ROTFS/var/www $ROTFS/var/log $ROTFS/etc

    # Kopierer filer fra host til container
    cp      /bin/busybox $ROTFS/bin/
    cp -pr  /opt/web_server/var/www/* $ROTFS/var/www/ ; chmod -rwx $ROTFS/var/www/jail.asis
    cp      /etc/mime.types $ROTFS/etc/ #; chmod +r $ROTFS/etc/mime.types
    gcc -static -o $ROTFS/bin/tjener $ROTFS/../mptjener.c

    # Oppretter busybox linker
    cd      $ROTFS/bin/
    for P in $(./busybox --list | grep -v busybox); do
        ln -s busybox $P
    done

    cat << EOF > $ROTFS/etc/initconf.sh
#!/bin/sh
# More startup configurations for container
#mount -t proc none /proc
EOF

    chmod +x $ROTFS/etc/initconf.sh

    # Oppretter inittab kall
    echo "::once:/bin/tjener" > $ROTFS/etc/inittab
    echo "::once:/etc/initconf.sh" >> $ROTFS/etc/inittab



    # Starter konteiner
    PATH=/bin           \
        unshare         \
        --user          \
        --map-root-user \
        --fork          \
        --pid           \
        --mount         \
        --cgroup        \
        --ipc           \
        --uts           \
        /usr/sbin/chroot $ROTFS bin/init &
}

# Dreper web_tjener prosessen, enten i daemon eller container modus
kill_tjener () {

    if [ -n "$DAEMON_PID" ]; then
        if [ "$EUID" -eq 0 ]; then
            kill -9 $DAEMON_PID
            rm -rf /opt/web_server/var/log/*
            echo "Stopper web_tjener daemon med PID: $DAEMON_PID"
        else
            echo "Trenger sudo/root for å stoppe daemon web tjener!";
        fi
    elif [ -n "$CONTAINER_PID" ]; then
        kill -9 $CONTAINER_PID
        rm -rf $ROTFS
        echo "Stopper web_tjener container med PID: $CONTAINER_PID"
    else
        echo "Ingen web_tjener å stoppe!"
        # Force flag for å slette container
        rm -rf $ROTFS
    fi
}

status_tjener () {
    if [ -n "$DAEMON_PID" ]; then
        echo "Web_tjener kjører som daemon med PID: $DAEMON_PID"
    elif [ -n "$CONTAINER_PID" ] ; then
        echo "Web_tjener kjører som conteiner med PID: $CONTAINER_PID"
    else
        echo "Ingen web_tjener kjører!"
        exit 0
    fi
}

start_tjener () {
    local MODE=$1

    if [ -z "$DAEMON_PID" ] && [ -z "$CONTAINER_PID" ]; then
        if [ $MODE = "daemon" ]; then
            stop_reverse_proxy
            gcc $WRKDIR/mptjener.c -o $WRKDIR/web_tjener
            echo "Starter web_tjener..."
            $WRKDIR/web_tjener
            sleep 1
            rm $WRKDIR/web_tjener
        elif [ $MODE = "container" ]; then
            start_reverse_proxy
            unshare_tjener
        else
            echo "Usage: ./tjener.sh start [daemon|container]"
        fi
    else
        echo "Web_tjener kjører allerede med PID: $DAEMON_PID $CONTAINER_PID"
        exit 0
    fi
}

restart_tjener () {
    if [ -n "$DAEMON_PID" ]; then
        local MODE="daemon"
    elif [ -n "$CONTAINER_PID" ] ; then
        local MODE="container"
    else
        echo "Ingen web_tjener kjører!"
        exit 0
    fi

    kill_tjener
    sleep 2
    start_tjener $MODE
}


start_reverse_proxy () {
    # Check if Apache is already running
    if ! systemctl is-active --quiet apache2; then
        echo "Apache is not running. Port 80 is not open. But 8080 is."
    fi
}

stop_reverse_proxy() {
    # Check if Apache is running
    if systemctl is-active --quiet apache2; then
        # Stop Apache
        echo "Stopping reverse-proxy..."
        a2dissite reverse-proxy.conf
        sleep 0.66
    fi
}

if [ "$1" = "kill" ] || [ "$1" = "stop" ]; then
    kill_tjener
elif [ "$1" = "status" ]; then
    status_tjener
elif [ "$1" = "start" ]; then
    if [ "$2" = "daemon" ] && [ "$EUID" -eq 0 ]; then
        start_tjener daemon
    elif [ "$2" = "container" ]; then
        start_tjener container
    else
        echo "Usage: ./tjener.sh start [container|daemon(sudo)]"
    fi
elif [ "$1" = "restart" ]; then
    restart_tjener
else
    echo "Usage: ./tjener.sh [{start container(non-sudo)|daemon(sudo)} | {kill|stop} | status | restart]"
fi

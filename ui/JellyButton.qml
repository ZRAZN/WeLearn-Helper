import QtQuick 2.15
import QtQuick.Controls 2.15

Button {
    id: root
    text: "按钮"
    font.pixelSize: 15
    font.bold: true
    
    property string btnColor: "#4CAF50"
    property string btnHoverColor: ""
    property string btnPressedColor: ""
    
    implicitWidth: 120
    implicitHeight: 45
    
    // 计算颜色
    property color baseColor: btnColor
    property color hoverColor: btnHoverColor || Qt.lighter(btnColor, 1.15)
    property color pressedColor: btnPressedColor || Qt.darker(btnColor, 1.2)
    
    background: Rectangle {
        id: bg
        radius: 12
        color: root.pressed ? root.pressedColor : 
               root.hovered ? root.hoverColor : root.baseColor
        opacity: 0.85
        
        // 顶部高光
        Rectangle {
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            height: parent.height * 0.4
            radius: parent.radius
            gradient: Gradient {
                GradientStop { position: 0.0; color: Qt.rgba(1, 1, 1, 0.3) }
                GradientStop { position: 1.0; color: Qt.rgba(1, 1, 1, 0) }
            }
        }
        
        // 边框高光
        border.width: 1
        border.color: Qt.rgba(1, 1, 1, 0.15)
        
        // 缩放动画
        scale: 1.0
        
        Behavior on color {
            ColorAnimation { duration: 150 }
        }
    }
    
    contentItem: Text {
        text: root.text
        font: root.font
        color: "white"
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
    }
    
    // 果冻状态
    states: [
        State {
            name: "pressed"
            when: root.pressed
            PropertyChanges { target: bg; scale: 0.90; opacity: 0.9 }
        },
        State {
            name: "hovered"
            when: root.hovered && !root.pressed
            PropertyChanges { target: bg; scale: 1.06; opacity: 0.88 }
        }
    ]
    
    transitions: [
        Transition {
            NumberAnimation {
                target: bg
                properties: "scale,opacity"
                duration: 100
                easing.type: Easing.InOutQuad
            }
        },
        Transition {
            from: "pressed"
            to: "*"
            NumberAnimation {
                target: bg
                properties: "scale,opacity"
                duration: 500
                easing.type: Easing.OutElastic
                easing.amplitude: 1.5
                easing.period: 0.25
            }
        }
    ]
}

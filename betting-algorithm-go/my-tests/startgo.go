package main

import (
	"fmt"
	"math"
)

var name string = "Stephen ondeche"
var age, favNum int = 32, 7
var homosexual bool = false

//var luckyNumAvg float64 = age/favNum

type Person struct {
	Name       string  `json: "name"`
	Age        int     `json: "age"`
	Homosexual bool    `json: "homosexual"`
	Country    string  `json: "country"`
	IdNumber   int     `json: "idNumber"`
	Height     float64 `json: "height"`
	Weight     float64 `json: "weight"`
}

var sondeche Person

func sum(nums ...int) int {
	total := 0
	for _, num := range nums {
		total += num
	}
	return total
}

// INTERFACES
type Shape interface {
	Area() float64
}

type Rectangle struct {
	width, height float64
}

type Circle struct {
	radius float64
}

func (r Rectangle) Area() float64 {
	return r.width * r.height
}

func (c Circle) Area() float64 {
	return math.Pi * c.radius * c.radius
}

func calculateArea(s Shape) float64 {
	return s.Area()
}

// END OF INTERFACES
func main() {
	//fmt.Println("Hello world!\nMy name is %w and I am %w years old", name, age)
	//if homosexual != true {
	//	fmt.Println("Congratulations! You are not Gay")
	//} else {
	//	fmt.Println("Why are you Gay!! 8(")
	//}
	//
	//fmt.Println(sum(45, 67, 89))
	//nums := []int{4, 5, 7}
	//fmt.Println(sum(nums))

	// INTERFACES
	//rect := Rectangle{width: 10, height: 5}
	//circle := Circle{radius: 5}
	// END OF INTERFACES

	i := 0
	for i < 5 {
		fmt.Println("i is ", i)
		i++
	}
}
